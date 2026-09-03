/* afl-fuzz-linucb.c
 *
 * Unified LinUCB queue prioritization + phase-bandit execution control.
 * - LinUCB: chooses which queue entry should be fuzzed next.
 * - Phase bandit: chooses how aggressively this seed should be fuzzed
 *   (det-friendly / balanced / deep-havoc / risk-havoc).
 * - Risk signals are consumed in candidate prefiltering, context building
 *   and reward computation.
 */

#include "afl-fuzz.h"
#include <float.h>
#include <math.h>
#include <string.h>

#ifndef LINUCB_DIM
  #define LINUCB_DIM 17u
#endif

#ifndef LINUCB_ALPHA
  #define LINUCB_ALPHA 0.90
#endif

#ifndef LINUCB_CANDIDATE_K
  #define LINUCB_CANDIDATE_K 24u
#endif

#ifndef LINUCB_MAX_CANDIDATES
  #define LINUCB_MAX_CANDIDATES 48u
#endif

#ifndef LINUCB_WARMUP_MIN_QUEUE
  #define LINUCB_WARMUP_MIN_QUEUE 16u
#endif

#ifndef LINUCB_WARMUP_MIN_EXECS
  #define LINUCB_WARMUP_MIN_EXECS 10000ULL
#endif

#ifndef LINUCB_WARMUP_MIN_UPDATES
  #define LINUCB_WARMUP_MIN_UPDATES 64ULL
#endif

#ifndef LINUCB_SAMPLE_ATTEMPT_MULT
  #define LINUCB_SAMPLE_ATTEMPT_MULT 8u
#endif

#ifndef LINUCB_L2_LAMBDA
  #define LINUCB_L2_LAMBDA 1.0
#endif

#define LINUCB_B_FORGET           0.995
#define LINUCB_REWARD_EMA_BETA    0.85
#define PHASE_REWARD_EMA_BETA     0.80
#define PHASE_WARMUP_PULLS        6ULL
#define PHASE_UCB_BETA            0.70
#define RISK_CTX_CLAMP            4.0

typedef struct phase_bandit_state {

  u64 pulls[PHASE_ARM_NUM];
  double reward_sum[PHASE_ARM_NUM];
  double reward_mean[PHASE_ARM_NUM];
  u64 total_pulls;

  u8 ep_arm;
  double ep_energy_mult;
  u8 ep_force_skip_det;
  u8 ep_force_det;

} phase_bandit_state_t;

typedef struct linucb_runtime {

  afl_state_t *afl;
  u32 dim;
  u32 candidate_k;
  double alpha;

  /* Online ridge-regression state */
  double *A_inv;     /* d x d */
  double *b;         /* d */
  double *theta;     /* d */
  double *tmp;       /* d scratch */
  double *ep_x;      /* d snapshot for current episode */

  /* Episode snapshot */
  struct queue_entry *ep_seed;
  u32 before_queued_items;
  u32 before_queued_with_cov;
  u64 before_saved_crashes;
  u64 before_saved_hangs;
  u64 before_saved_tmouts;
  u64 before_total_execs;

  u32 before_risk_total_hits;
  u32 before_risk_target_hits;
  u8 before_risk_max_level;
  double before_risk_score;

  u64 updates;

  phase_bandit_state_t phase;

  struct linucb_runtime *next;

} linucb_runtime_t;

static linucb_runtime_t *g_linucb_head = NULL;

static inline double linucb_clampd(double v, double lo, double hi) {

  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;

}

static inline double linucb_log2_1p_u64(u64 v) {

  return log2(1.0 + (double)v);

}

static inline double linucb_log2_1p_u32(u32 v) {

  return log2(1.0 + (double)v);

}

static linucb_runtime_t *linucb_runtime_find(afl_state_t *afl) {

  linucb_runtime_t *rt = g_linucb_head;
  while (rt) {

    if (rt->afl == afl) return rt;
    rt = rt->next;

  }

  return NULL;

}

static linucb_runtime_t *linucb_runtime_create(afl_state_t *afl) {

  linucb_runtime_t *rt = linucb_runtime_find(afl);
  if (rt) return rt;

  rt = ck_alloc(sizeof(linucb_runtime_t));
  rt->afl = afl;
  rt->dim = LINUCB_DIM;
  rt->candidate_k = LINUCB_CANDIDATE_K;
  if (rt->candidate_k > LINUCB_MAX_CANDIDATES) {

    rt->candidate_k = LINUCB_MAX_CANDIDATES;

  }

  rt->alpha = LINUCB_ALPHA;

  rt->A_inv = ck_alloc(sizeof(double) * rt->dim * rt->dim);
  rt->b = ck_alloc(sizeof(double) * rt->dim);
  rt->theta = ck_alloc(sizeof(double) * rt->dim);
  rt->tmp = ck_alloc(sizeof(double) * rt->dim);
  rt->ep_x = ck_alloc(sizeof(double) * rt->dim);

  /* A = lambda * I => A_inv = (1/lambda) * I */
  {
    double diag = 1.0 / LINUCB_L2_LAMBDA;
    for (u32 i = 0; i < rt->dim; ++i) {

      rt->A_inv[i * rt->dim + i] = diag;

    }
  }

  rt->phase.ep_arm = PHASE_ARM_BALANCED;
  rt->phase.ep_energy_mult = 1.0;

  rt->next = g_linucb_head;
  g_linucb_head = rt;
  return rt;

}

static void linucb_runtime_destroy(afl_state_t *afl) {

  linucb_runtime_t **pp = &g_linucb_head;
  while (*pp) {

    linucb_runtime_t *rt = *pp;
    if (rt->afl == afl) {

      *pp = rt->next;
      ck_free(rt->A_inv);
      ck_free(rt->b);
      ck_free(rt->theta);
      ck_free(rt->tmp);
      ck_free(rt->ep_x);
      ck_free(rt);
      return;

    }

    pp = &((*pp)->next);

  }

}

static inline u32 linucb_alias_pick(afl_state_t *afl) {

  if (unlikely(!afl->queued_items)) return 0;

  if (likely(afl->alias_probability && afl->alias_table)) {

    u32 s = rand_below(afl, afl->queued_items);
    double p = rand_next_percent(afl);
    return (p < afl->alias_probability[s] ? s : afl->alias_table[s]);

  }

  return rand_below(afl, afl->queued_items);

}

static inline struct queue_entry *linucb_q_at(afl_state_t *afl, u32 idx) {

  if (unlikely(idx >= afl->queued_items)) return NULL;
  return afl->queue_buf[idx];

}

static double linucb_risk_metric(afl_state_t *afl, struct queue_entry *q) {

  if (unlikely(!afl || !q || !afl->risk_sched_enabled || !q->risk_seen)) return 0.0;

  double hot = 0.0;
  for (u32 i = 0; i < RISK_HOT_ARRAY_SIZE; ++i) {

    hot += (double)(i + 1) * (double)q->risk_hot[i];

  }

  double score = q->risk_score;
  score += 0.15 * linucb_log2_1p_u32(q->risk_total_hits);
  score += 0.30 * linucb_log2_1p_u32(q->risk_target_hits);
  score += 0.25 * (double)q->risk_max_level;
  score += 0.02 * hot;

  if (q->mother && q->mother->risk_seen) {

    score += 0.10 * q->mother->risk_score;

  }

  return linucb_clampd(score, 0.0, RISK_CTX_CLAMP);

}

static void linucb_build_ctx(afl_state_t *afl, struct queue_entry *q, double *x) {

  memset(x, 0, sizeof(double) * LINUCB_DIM);
  if (unlikely(!q)) return;

  const double n_fuzz =
      (afl->n_fuzz ? (double)afl->n_fuzz[q->n_fuzz_entry] : 0.0);
  const double risk = linucb_risk_metric(afl, q);
  const double parent_risk =
      (q->mother && q->mother->risk_seen)
          ? linucb_clampd(q->mother->risk_score, 0.0, RISK_CTX_CLAMP)
          : 0.0;

  x[0] = 1.0;
  x[1] = q->favored ? 1.0 : 0.0;
  x[2] = q->was_fuzzed ? 0.0 : 1.0;
  x[3] = q->has_new_cov ? 1.0 : 0.0;
  x[4] = linucb_clampd((double)q->depth / 64.0, 0.0, 2.0);
  x[5] = 1.0 / (1.0 + linucb_log2_1p_u32(q->len));
  x[6] = 1.0 / (1.0 + linucb_log2_1p_u64(q->exec_us));
  x[7] = linucb_clampd(linucb_log2_1p_u32(q->bitmap_size) / 16.0, 0.0, 2.0);
  x[8] = 1.0 / (1.0 + log2(1.0 + n_fuzz));
  x[9] = linucb_clampd((double)q->handicap / 16.0, 0.0, 2.0);
  x[10] = q->fs_redundant ? 1.0 : 0.0;

  /* New risk-aware / recency-aware features */
  x[11] = risk / RISK_CTX_CLAMP;
  x[12] = linucb_clampd((double)q->risk_max_level / 4.0, 0.0, 2.0);
  x[13] = linucb_clampd(linucb_log2_1p_u32(q->risk_target_hits) / 4.0, 0.0, 2.0);
  x[14] = parent_risk / RISK_CTX_CLAMP;
  x[15] = linucb_clampd(q->lin_reward_ema / 8.0, -1.5, 2.0);
  x[16] = linucb_clampd(q->phase_reward_ema / 8.0, -1.5, 2.0);

}

static void linucb_matvec(const double *A, const double *x, double *out,
                          u32 dim) {

  for (u32 i = 0; i < dim; ++i) {

    double acc = 0.0;
    const double *row = &A[i * dim];
    for (u32 j = 0; j < dim; ++j) {

      acc += row[j] * x[j];

    }

    out[i] = acc;

  }

}

static double linucb_dot(const double *a, const double *b, u32 dim) {

  double acc = 0.0;
  for (u32 i = 0; i < dim; ++i) {

    acc += a[i] * b[i];

  }

  return acc;

}

static double linucb_score(linucb_runtime_t *rt, afl_state_t *afl,
                           struct queue_entry *q, double *mean_out,
                           double *bonus_out) {

  double x[LINUCB_DIM];
  linucb_build_ctx(afl, q, x);

  linucb_matvec(rt->A_inv, x, rt->tmp, rt->dim);

  const double mean = linucb_dot(rt->theta, x, rt->dim);
  const double quad = linucb_dot(x, rt->tmp, rt->dim);
  const double bonus = rt->alpha * sqrt(quad > 0.0 ? quad : 0.0);

  if (mean_out) *mean_out = mean;
  if (bonus_out) *bonus_out = bonus;
  return mean + bonus;

}

static void linucb_update(linucb_runtime_t *rt, const double *x,
                          double reward) {

  linucb_matvec(rt->A_inv, x, rt->tmp, rt->dim);
  const double denom = 1.0 + linucb_dot(x, rt->tmp, rt->dim);

  if (likely(denom > 1e-12)) {

    for (u32 i = 0; i < rt->dim; ++i) {

      for (u32 j = 0; j < rt->dim; ++j) {

        rt->A_inv[i * rt->dim + j] -= (rt->tmp[i] * rt->tmp[j]) / denom;

      }

    }

  }

  for (u32 i = 0; i < rt->dim; ++i) {

    rt->b[i] *= LINUCB_B_FORGET;
    rt->b[i] += reward * x[i];

  }

  linucb_matvec(rt->A_inv, rt->b, rt->theta, rt->dim);
  ++rt->updates;

}

static inline double linucb_delta_u64(u64 now, u64 before) {

  return (now >= before) ? (double)(now - before) : 0.0;

}

static inline double linucb_delta_u32(u32 now, u32 before) {

  return (now >= before) ? (double)(now - before) : 0.0;

}

static void linucb_push_candidate(u32 *cand_ids, u32 *cand_count, u32 idx) {

  for (u32 i = 0; i < *cand_count; ++i) {

    if (cand_ids[i] == idx) return;

  }

  if (*cand_count < LINUCB_MAX_CANDIDATES) {

    cand_ids[(*cand_count)++] = idx;

  }

}

static void linucb_add_risk_frontier(afl_state_t *afl, u32 *cand_ids,
                                     u32 *cand_count) {

  if (!afl->risk_sched_enabled) return;

  double best_score[3] = {-DBL_MAX, -DBL_MAX, -DBL_MAX};
  u32 best_idx[3] = {(u32)-1, (u32)-1, (u32)-1};

  for (u32 i = 0; i < afl->queued_items; ++i) {

    struct queue_entry *q = linucb_q_at(afl, i);
    if (unlikely(!q || q->disabled || !q->risk_seen)) continue;

    double s = linucb_risk_metric(afl, q);
    if (s <= 0.0) continue;

    for (u32 slot = 0; slot < 3; ++slot) {

      if (s > best_score[slot]) {

        for (u32 shift = 2; shift > slot; --shift) {

          best_score[shift] = best_score[shift - 1];
          best_idx[shift] = best_idx[shift - 1];

        }

        best_score[slot] = s;
        best_idx[slot] = i;
        break;

      }

    }

  }

  for (u32 i = 0; i < 3; ++i) {

    if (best_idx[i] != (u32)-1) linucb_push_candidate(cand_ids, cand_count, best_idx[i]);

  }

}

static void linucb_add_tail_frontier(afl_state_t *afl, u32 *cand_ids,
                                     u32 *cand_count) {

  u32 added = 0;
  for (s32 i = (s32)afl->queued_items - 1; i >= 0 && added < 4; --i) {

    struct queue_entry *q = linucb_q_at(afl, (u32)i);
    if (unlikely(!q || q->disabled)) continue;

    u32 hits = 0;
    if (afl->n_fuzz) hits = afl->n_fuzz[q->n_fuzz_entry];

    if (!q->was_fuzzed || hits <= 2) {

      linucb_push_candidate(cand_ids, cand_count, (u32)i);
      ++added;

    }

  }

}

static double phase_context_bonus(afl_state_t *afl, struct queue_entry *q,
                                  u8 arm) {

  const double risk = linucb_risk_metric(afl, q) / RISK_CTX_CLAMP;
  const double fresh = q->was_fuzzed ? 0.0 : 1.0;
  const double depth = linucb_clampd((double)q->depth / 32.0, 0.0, 2.0);
  const double cheap = 1.0 / (1.0 + linucb_log2_1p_u64(q->exec_us));
  const double rare = linucb_clampd(linucb_log2_1p_u32(q->bitmap_size) / 16.0,
                                    0.0, 2.0);
  const double n_fuzz =
      (afl->n_fuzz ? (double)afl->n_fuzz[q->n_fuzz_entry] : 0.0);
  const double underexplored = 1.0 / (1.0 + log2(1.0 + n_fuzz));

  switch (arm) {

    case PHASE_ARM_DET:
      return 0.40 * fresh + 0.20 * (q->favored ? 1.0 : 0.0) + 0.10 * cheap;

    case PHASE_ARM_BALANCED:
      return 0.15 * (q->has_new_cov ? 1.0 : 0.0) + 0.10 * rare +
             0.10 * underexplored;

    case PHASE_ARM_DEEP:
      return 0.25 * depth + 0.20 * underexplored + 0.10 * rare;

    case PHASE_ARM_RISK:
      return 0.50 * risk + 0.10 * depth + 0.10 * underexplored;

    default:
      return 0.0;

  }

}

static void phase_apply_action(afl_state_t *afl, u8 arm, double *energy_mult,
                               u8 *force_skip_det, u8 *force_det) {

  (void)afl;

  *energy_mult = 1.0;
  *force_skip_det = 0;
  *force_det = 0;

  switch (arm) {

    case PHASE_ARM_DET:
      *energy_mult = 0.85;
      *force_det = 1;
      break;

    case PHASE_ARM_BALANCED:
      *energy_mult = 1.00;
      break;

    case PHASE_ARM_DEEP:
      *energy_mult = 1.25;
      *force_skip_det = 1;
      break;

    case PHASE_ARM_RISK:
      *energy_mult = 1.35;
      *force_skip_det = 1;
      break;

    default:
      break;

  }

}

static u8 phase_select_arm(linucb_runtime_t *rt, afl_state_t *afl,
                           struct queue_entry *q) {

  for (u8 arm = 0; arm < PHASE_ARM_NUM; ++arm) {

    if (rt->phase.pulls[arm] < PHASE_WARMUP_PULLS) return arm;

  }

  double best = -DBL_MAX;
  u8 best_arm = PHASE_ARM_BALANCED;
  const double total = (double)rt->phase.total_pulls + 1.0;

  for (u8 arm = 0; arm < PHASE_ARM_NUM; ++arm) {

    double mean = rt->phase.reward_mean[arm];
    double bonus =
        PHASE_UCB_BETA *
        sqrt(log(total) / (double)(rt->phase.pulls[arm] ? rt->phase.pulls[arm] : 1));
    double ctx = phase_context_bonus(afl, q, arm);
    double score = mean + bonus + ctx;

    if (score > best) {

      best = score;
      best_arm = arm;

    }

  }

  return best_arm;

}

static double linucb_compute_reward(linucb_runtime_t *rt, afl_state_t *afl,
                                    struct queue_entry *q, u8 skipped) {

  double reward = 0.0;

  reward += 3.0 * linucb_delta_u32(afl->queued_items, rt->before_queued_items);
  reward +=
      2.0 * linucb_delta_u32(afl->queued_with_cov, rt->before_queued_with_cov);
  reward += 8.0 * linucb_delta_u64(afl->saved_crashes, rt->before_saved_crashes);
  reward += 4.0 * linucb_delta_u64(afl->saved_hangs, rt->before_saved_hangs);
  reward += 1.5 * linucb_delta_u64(afl->saved_tmouts, rt->before_saved_tmouts);

  if (q) {

    double risk_total =
        linucb_delta_u32(q->risk_total_hits, rt->before_risk_total_hits);
    double risk_target =
        linucb_delta_u32(q->risk_target_hits, rt->before_risk_target_hits);
    double risk_score_gain =
        (q->risk_score > rt->before_risk_score)
            ? (q->risk_score - rt->before_risk_score)
            : 0.0;
    double risk_level_gain =
        (q->risk_max_level > rt->before_risk_max_level)
            ? (double)(q->risk_max_level - rt->before_risk_max_level)
            : 0.0;

    reward += 1.2 * linucb_log2_1p_u32((u32)risk_total);
    reward += 2.0 * linucb_log2_1p_u32((u32)risk_target);
    reward += 4.0 * risk_score_gain;
    reward += 0.8 * risk_level_gain;

  }

  {
    double exec_delta =
        linucb_delta_u64(afl->fsrv.total_execs, rt->before_total_execs);
    reward -= 0.20 * log2(1.0 + exec_delta);
  }

  if (skipped) reward -= 0.50;
  return linucb_clampd(reward, -3.0, 16.0);

}

static double phase_compute_reward(linucb_runtime_t *rt, afl_state_t *afl,
                                   struct queue_entry *q, u8 skipped) {

  double reward = 0.0;

  reward +=
      2.5 * linucb_delta_u32(afl->queued_with_cov, rt->before_queued_with_cov);
  reward += 7.0 * linucb_delta_u64(afl->saved_crashes, rt->before_saved_crashes);
  reward += 4.0 * linucb_delta_u64(afl->saved_hangs, rt->before_saved_hangs);
  reward += 1.0 * linucb_delta_u64(afl->saved_tmouts, rt->before_saved_tmouts);

  if (q) {

    double risk_total =
        linucb_delta_u32(q->risk_total_hits, rt->before_risk_total_hits);
    double risk_target =
        linucb_delta_u32(q->risk_target_hits, rt->before_risk_target_hits);
    double risk_score_gain =
        (q->risk_score > rt->before_risk_score)
            ? (q->risk_score - rt->before_risk_score)
            : 0.0;

    reward += 1.5 * linucb_log2_1p_u32((u32)risk_total);
    reward += 2.5 * linucb_log2_1p_u32((u32)risk_target);
    reward += 4.5 * risk_score_gain;

  }

  {
    double exec_delta =
        linucb_delta_u64(afl->fsrv.total_execs, rt->before_total_execs);
    reward -= 0.16 * log2(1.0 + exec_delta);
  }

  if (skipped) reward -= 0.40;
  return linucb_clampd(reward, -3.0, 18.0);

}

void linucb_init(afl_state_t *afl) {

  if (unlikely(!afl)) return;
  if (!afl->linucb_mode) return;
  (void)linucb_runtime_create(afl);

}

void linucb_deinit(afl_state_t *afl) {

  if (unlikely(!afl)) return;
  linucb_runtime_destroy(afl);

}

u8 linucb_warmup_active(afl_state_t *afl) {

  if (unlikely(!afl) || !afl->linucb_mode) return 0;

  linucb_runtime_t *rt = linucb_runtime_find(afl);
  if (!rt) return 1;

  if (afl->queued_items < LINUCB_WARMUP_MIN_QUEUE) return 1;
  if (afl->fsrv.total_execs < LINUCB_WARMUP_MIN_EXECS) return 1;
  if (rt->updates < LINUCB_WARMUP_MIN_UPDATES) return 1;

  return 0;

}

u32 linucb_select_next_queue_entry(afl_state_t *afl) {

  if (unlikely(!afl || !afl->queued_items)) return 0;
  if (unlikely(afl->old_seed_selection)) return afl->current_entry;

  linucb_runtime_t *rt = linucb_runtime_find(afl);
  if (!rt) rt = linucb_runtime_create(afl);

  if (unlikely(linucb_warmup_active(afl))) {

    u32 id;
    do {

      id = linucb_alias_pick(afl);

    } while (unlikely(id >= afl->queued_items));

    return id;

  }

  u32 cand_need =
      (rt->candidate_k < afl->queued_items) ? rt->candidate_k : afl->queued_items;
  if (cand_need > LINUCB_MAX_CANDIDATES) cand_need = LINUCB_MAX_CANDIDATES;

  u32 cand_ids[LINUCB_MAX_CANDIDATES];
  u32 cand_count = 0;

  if (likely(afl->pending_favored && afl->smallest_favored >= 0)) {

    linucb_push_candidate(cand_ids, &cand_count, (u32)afl->smallest_favored);

  }

  linucb_add_risk_frontier(afl, cand_ids, &cand_count);
  linucb_add_tail_frontier(afl, cand_ids, &cand_count);

  {
    u32 attempts = cand_need * LINUCB_SAMPLE_ATTEMPT_MULT;
    if (attempts < cand_need) attempts = cand_need;

    while (cand_count < cand_need && attempts--) {

      u32 idx = linucb_alias_pick(afl);
      struct queue_entry *q = linucb_q_at(afl, idx);
      if (unlikely(idx >= afl->queued_items || !q || q->disabled)) continue;
      linucb_push_candidate(cand_ids, &cand_count, idx);

    }
  }

  if (!cand_count) {

    for (u32 i = 0; i < afl->queued_items; ++i) {

      struct queue_entry *q = linucb_q_at(afl, i);
      if (q && !q->disabled) return i;

    }

    return (afl->current_entry < afl->queued_items) ? afl->current_entry : 0;

  }

  u32 best_idx = cand_ids[0];
  double best_score = -DBL_MAX;

  for (u32 i = 0; i < cand_count; ++i) {

    struct queue_entry *q = linucb_q_at(afl, cand_ids[i]);
    if (unlikely(!q || q->disabled)) continue;

    double mean = 0.0, bonus = 0.0;
    double score = linucb_score(rt, afl, q, &mean, &bonus);

    q->lin_last_mean = mean;
    q->lin_last_ucb = score;

    if (score > best_score) {

      best_score = score;
      best_idx = cand_ids[i];

    }

  }

  return best_idx;

}

void linucb_begin_episode(afl_state_t *afl, struct queue_entry *q) {

  if (unlikely(!afl || !afl->linucb_mode || !q)) return;

  linucb_runtime_t *rt = linucb_runtime_find(afl);
  if (!rt) rt = linucb_runtime_create(afl);

  rt->ep_seed = q;
  linucb_build_ctx(afl, q, rt->ep_x);

  rt->before_queued_items = afl->queued_items;
  rt->before_queued_with_cov = afl->queued_with_cov;
  rt->before_saved_crashes = afl->saved_crashes;
  rt->before_saved_hangs = afl->saved_hangs;
  rt->before_saved_tmouts = afl->saved_tmouts;
  rt->before_total_execs = afl->fsrv.total_execs;

  rt->before_risk_total_hits = q->risk_total_hits;
  rt->before_risk_target_hits = q->risk_target_hits;
  rt->before_risk_max_level = q->risk_max_level;
  rt->before_risk_score = q->risk_score;

  {
    u8 arm = phase_select_arm(rt, afl, q);
    double energy = 1.0;
    u8 force_skip_det = 0;
    u8 force_det = 0;

    phase_apply_action(afl, arm, &energy, &force_skip_det, &force_det);

    rt->phase.ep_arm = arm;
    rt->phase.ep_energy_mult = energy;
    rt->phase.ep_force_skip_det = force_skip_det;
    rt->phase.ep_force_det = force_det;

    afl->phase_cur_arm = arm;
    afl->phase_energy_mult = energy;
    afl->phase_force_skip_det = force_skip_det;
    afl->phase_force_det = force_det;
  }

}

void linucb_finish_episode(afl_state_t *afl, struct queue_entry *q, u8 skipped) {

  if (unlikely(!afl || !afl->linucb_mode)) return;

  linucb_runtime_t *rt = linucb_runtime_find(afl);
  if (!rt || !rt->ep_seed) return;

  (void)q;
  struct queue_entry *seed = rt->ep_seed;

  {
    double reward = linucb_compute_reward(rt, afl, seed, skipped);
    linucb_update(rt, rt->ep_x, reward);

    seed->lin_selects += 1;
    seed->lin_last_reward = reward;
    seed->lin_reward_ema =
        (seed->lin_selects <= 1)
            ? reward
            : (LINUCB_REWARD_EMA_BETA * seed->lin_reward_ema +
               (1.0 - LINUCB_REWARD_EMA_BETA) * reward);
  }

  {
    u8 arm = rt->phase.ep_arm;
    double reward = phase_compute_reward(rt, afl, seed, skipped);

    rt->phase.pulls[arm] += 1;
    rt->phase.total_pulls += 1;
    rt->phase.reward_sum[arm] += reward;
    rt->phase.reward_mean[arm] =
        rt->phase.reward_sum[arm] / (double)rt->phase.pulls[arm];

    seed->phase_selects[arm] += 1;
    seed->phase_last_arm = arm;
    seed->phase_reward_ema =
        (seed->phase_selects[arm] <= 1)
            ? reward
            : (PHASE_REWARD_EMA_BETA * seed->phase_reward_ema +
               (1.0 - PHASE_REWARD_EMA_BETA) * reward);

    afl->phase_last_reward = reward;
  }

  rt->ep_seed = NULL;

  afl->phase_cur_arm = PHASE_ARM_BALANCED;
  afl->phase_energy_mult = 1.0;
  afl->phase_force_skip_det = 0;
  afl->phase_force_det = 0;

}