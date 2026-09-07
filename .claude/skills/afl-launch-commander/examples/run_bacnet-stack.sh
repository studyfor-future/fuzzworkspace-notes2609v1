#!/usr/bin/env bash
# =============================================================================
# run_bacnet-stack.sh —— AFL/aflmy 一键启动脚本（示例产物，可直接运行）
#
# 本脚本是 afl-launch-commander 技能生成/参考的「首个可直接运行产物」。
# 运行位置：Docker 容器内（默认容器 myafl-test-ubuntu24，路径 /opt/aflmy-test/1/...）。
#
# 【明文替换渠道】：
#   下方「========== 可手动修改 · 明文替换渠道 ==========」区域内的每一个值都是
#   明文，人工只需改这里；其余「固定逻辑」区域（前置校验 / 命令组装 / 执行）不要动。
#   留空（"" 或空）的槽位表示不启用该选项。
# =============================================================================

set -euo pipefail

# =============================================================================
# ========== 可手动修改 · 明文替换渠道（人工只改这一块）==========
# =============================================================================

PROTOCOL="bacnet-stack"                                  # 协议/项目名
SLOT_ROOT="/opt/aflmy-test/1"                            # 各协议 target 根目录
TARGET="${SLOT_ROOT}/${PROTOCOL}/target"                 # 普通 target 软链接（编译产物）
TARGET_CMPLOG="${SLOT_ROOT}/${PROTOCOL}/target_cmplog"   # CmpLog target 软链接

# ↓ 输入语料目录：请确认/替换为你的真实 seeds 路径（Enriched_seed_generate 生成的语料）
INPUT_DIR="${SLOT_ROOT}/${PROTOCOL}/seeds"

# ↓ 输出目录：默认带时间戳避免覆盖；也可改成固定路径（如 .../out-fixed），但不要与已存在结果重名
OUTPUT_DIR="${SLOT_ROOT}/${PROTOCOL}/out-$(date +%Y%m%d-%H%M%S)"

AFL_BIN="/opt/aflmy/afl-fuzz"                            # 或 /opt/fuzz-bin/aflmy-fuzz
MEM_LIMIT="none"                                         # -m：内存上限（none 或具体 MB）
TIMEOUT_MS="1000"                                        # -t：单次执行超时(ms)
RUN_SECONDS="0"                                          # -V：总运行秒数（0=不限时）
DICT=""                                                  # -x：字典路径，留空=不启用
CMPLOG=1                                                 # 1=启用 -c target_cmplog；0=关闭
SLOTS=1                                                  # 并行实例数（>1 时：1 个 master + N-1 个 slave）

# ↓ 目标程序参数：@@ = 输入文件占位（AFL 文件模式）；若目标走 stdin 则留空 ""
#   若目标为网络服务（server 类），请确认是否已接网络桥接 harness，再决定此值
TARGET_ARGS="@@"

# =============================================================================
# ========== 固定逻辑（通常无需修改）==========
# =============================================================================

# AFL 运行环境（与已验证命令保持一致）
export AFL_QUIET=1
export AFL_SKIP_CPUFREQ=1
export AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

# ---- 前置校验 ----
[ -x "$TARGET" ] || { echo "[x] target 不存在或不可执行: $TARGET" >&2; exit 1; }
[ -d "$INPUT_DIR" ] || { echo "[x] 输入语料目录不存在: $INPUT_DIR" >&2; exit 1; }
[ ! -e "$OUTPUT_DIR" ] || { echo "[x] 输出目录已存在，为避免覆盖请改 OUTPUT_DIR: $OUTPUT_DIR" >&2; exit 1; }

# ---- 组装并执行 ----
run_one() {  # $1 = 角色标识（single / master / 从实例编号）
  local role="$1"
  local args=(-i "$INPUT_DIR" -o "$OUTPUT_DIR" -m "$MEM_LIMIT" -t "$TIMEOUT_MS")
  [ -n "$DICT" ] && args+=(-x "$DICT")
  [ "$RUN_SECONDS" != "0" ] && args+=(-V "$RUN_SECONDS")
  if [ "$CMPLOG" = "1" ] && [ -x "$TARGET_CMPLOG" ]; then
    args+=(-c "$TARGET_CMPLOG")
  fi
  if [ "$role" = "master" ]; then
    args+=(-M "master")
  elif [ "$role" != "single" ]; then
    args+=(-S "slave_${role}")
  fi
  args+=(-- "$TARGET" $TARGET_ARGS)

  echo "[run:${role}] $AFL_BIN ${args[*]}"
  "$AFL_BIN" "${args[@]}"
}

if [ "$SLOTS" -le 1 ]; then
  run_one single
else
  run_one master &
  for ((i = 1; i < SLOTS; i++)); do run_one "$i" & done
  wait
fi
