#!/usr/bin/env bash
set -euo pipefail

: "${RISKINS_WORKBASE:?}"
OUT_ROOT="$RISKINS_WORKBASE/fuzz-out"

if [[ ! -d "$OUT_ROOT" ]]; then
  echo "fuzz output directory not found: $OUT_ROOT" >&2
  exit 1
fi

print_one() {
  local case_dir="$1"
  local name
  name="$(basename "$case_dir")"
  local fstats="$case_dir/default/fuzzer_stats"

  echo "============================================================"
  echo "CASE: $name"
  echo "DIR : $case_dir"
  echo "============================================================"

  if [[ -f "$fstats" ]]; then
    grep -E '^(command_line|run_time|execs_done|execs_per_sec|cycles_done|corpus_count|saved_crashes|saved_hangs|pending_total|max_depth|stability|bitmap_cvg|edges_found|var_byte_count|slowest_exec_ms)\s*:' "$fstats" || cat "$fstats"
  else
    echo "missing fuzzer_stats"
  fi

  if [[ -d "$case_dir/default/queue" ]]; then
    echo "queue_files=$(find "$case_dir/default/queue" -maxdepth 1 -type f | wc -l)"
  fi

  if [[ -d "$case_dir/default/crashes" ]]; then
    echo "crash_files=$(find "$case_dir/default/crashes" -maxdepth 1 -type f ! -name README.txt | wc -l)"
  fi

  if [[ -d "$case_dir/default/hangs" ]]; then
    echo "hang_files=$(find "$case_dir/default/hangs" -maxdepth 1 -type f | wc -l)"
  fi

  local clog="$case_dir.console.log"
  if [[ -f "$clog" ]]; then
    echo "--- tail: $clog ---"
    tail -n 30 "$clog" || true
  fi

  echo
}

for d in "$OUT_ROOT"/*; do
  [[ -d "$d" ]] || continue
  print_one "$d"
done