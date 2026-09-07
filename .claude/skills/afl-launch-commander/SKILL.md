---
name: afl-launch-commander
description: 把已验证正确的 AFL/aflmy 启动运行命令参数化并生成/演进一键启动脚本。当用户提供一条“测试运行正确”的 fuzz 命令、要求生成/调整/优化 AFL 启动命令、要求一键启动脚本、多实例(slot)并行启动，或报告代码改动需要同步更新启动命令时使用。参考原始模板(本文“原始模板”节与 E:\workspace\code\analysis\analysis-myafl-test\整理的build_commands\20260816_aflmy_slot1_regular_and_cmplog_build_commands.md)，按每次用户给的参数自动调参，并在既有命令基础上增量进化以适配用户自定义代码。
---

# Skill: afl-launch-commander

## 1. 本文件的作用

把“AFL/aflmy 重复启动运行命令”固化成一个可复用的命令生成器：用户每次只给**变化的参数**，Agent 参考**原始模板**自动补齐、调整并产出一条可直接执行的一键启动脚本；用户报告代码改动时，在**上一次已验证命令**基础上做增量进化，而不是每次都从零拼命令。

核心产物 = 一个「参数集中在顶部、可直接运行」的脚本（in-container bash，可按需再包一层宿主机 `.bat`）。

## 2. 原始模板（必须参考的基线）

> 该模板来自已成功运行的编译命令整理与 aflmy 测试脚本。Agent 生成命令时，默认保留以下骨架与变量，除非用户明确要求改变。

### 2.1 宿主机 → 容器包装（Windows 宿主机）

```bat
docker compose -f <COMPOSE_FILE> exec <SERVICE> bash -lc "<容器内命令>"
```

已知默认值（可被用户参数覆盖）：

| 键 | 默认 | 说明 |
|---|---|---|
| `COMPOSE_FILE` | `D:\VM\codex-dev\analysis\analysis-myafl-test\resources\docker-compose.myafl-test.yml` | compose 文件 |
| `SERVICE` | `myafl-test-ubuntu24` | 容器服务名 |

### 2.2 容器内运行环境（在 fuzz 命令前导出）

```bash
export AFL_QUIET=1
export AFL_SKIP_CPUFREQ=1
export AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
```

（编译才需要 `CC/CXX/CFLAGS/LDFLAGS/AFL_LLVM_CMPLOG`，纯运行不需要，见 §7 进化规则。）

### 2.3 afl-fuzz 规范命令骨架

```bash
<AFL_BIN> -i <INPUT_DIR> -o <OUTPUT_DIR> \
  [-m <MEM_LIMIT>] [-t <TIMEOUT_MS>] [-V <RUN_SECONDS>] [-x <DICT>] \
  [-M <master_id> | -S <slave_id>] [-c <TARGET_CMPLOG>] \
  -- <TARGET> [<TARGET_ARGS>... @@]
```

已知默认值：

| 键 | 默认 | 说明 |
|---|---|---|
| `AFL_BIN` | `/opt/aflmy/afl-fuzz`（或 wrapper `/opt/fuzz-bin/aflmy-fuzz`） | fuzz 二进制 |
| `TARGET` | `/opt/aflmy-test/1/<protocol>/target` | 普通 target 软链接 |
| `TARGET_CMPLOG` | `/opt/aflmy-test/1/<protocol>/target_cmplog` | CmpLog target 软链接 |
| `SLOT_ROOT` | `/opt/aflmy-test/1` | 各协议 target 根目录 |

### 2.4 五个已知协议（`<protocol>` 取值）

`bacnet-stack`、`lib60870`、`libiec61850`、`libmodbus`、`OpENer`。用户自定义代码时，`<protocol>` 与 `TARGET` 路径按用户给的信息替换。

## 3. 【可配置区】（参数槽位，明文定义，人工/Agent 均可改）

Agent 每次只需问清“这次变了哪些参数”，其余全部沿用模板默认或上一次的值：

```text
# ===== AFL 启动参数槽位（每次运行按需填写，留空=用默认/上次值）=====
PROTOCOL      = bacnet-stack          # 协议名（或自定义项目名）
TARGET        = {SLOT_ROOT}/{PROTOCOL}/target        # 普通 target 路径
TARGET_CMPLOG = {SLOT_ROOT}/{PROTOCOL}/target_cmplog # CmpLog target 路径（可空）
INPUT_DIR     = {SLOT_ROOT}/{PROTOCOL}/seeds         # -i 输入语料目录
OUTPUT_DIR    = {SLOT_ROOT}/{PROTOCOL}/out-{时间戳}  # -o 输出（默认不覆盖既有结果）
AFL_BIN       = /opt/aflmy/afl-fuzz                   # fuzz 二进制
MEM_LIMIT     = none                  # -m（none / 具体 MB）
TIMEOUT_MS    = 1000                  # -t
RUN_SECONDS   = 0                     # -V（0=不限时）
DICT          =                       # -x 字典路径（可空）
CMPLOG        = 1                     # 1=启用 -c target_cmplog；0=关闭
SLOTS         = 1                     # 并行实例数（>1 时 -M master + N-1 个 -S）
TARGET_ARGS   = @@                    # 目标程序参数；@@=输入文件占位，stdin 模式则留空
COMPOSE_FILE  = <见 §2.1 默认>
SERVICE       = myafl-test-ubuntu24
# ===== 槽位结束 =====
```

## 4. 一键启动脚本模板（生成产物）

Agent 生成的脚本把 §3 的槽位转成顶部变量，正文做**前置校验 + 组装命令 + 执行**。模板如下（`@@` 与各变量按 §3 填入）：

```bash
#!/usr/bin/env bash
set -euo pipefail

# ===== 可配置参数（本次运行）=====
PROTOCOL="bacnet-stack"
SLOT_ROOT="/opt/aflmy-test/1"
TARGET="${SLOT_ROOT}/${PROTOCOL}/target"
TARGET_CMPLOG="${SLOT_ROOT}/${PROTOCOL}/target_cmplog"
INPUT_DIR="${SLOT_ROOT}/${PROTOCOL}/seeds"
OUTPUT_DIR="${SLOT_ROOT}/${PROTOCOL}/out-$(date +%Y%m%d-%H%M%S)"
AFL_BIN="/opt/aflmy/afl-fuzz"
MEM_LIMIT="none"
TIMEOUT_MS="1000"
RUN_SECONDS="0"
DICT=""
CMPLOG=1
SLOTS=1
TARGET_ARGS="@@"
# ===== 参数结束 =====

export AFL_QUIET=1
export AFL_SKIP_CPUFREQ=1
export AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

# 前置校验：target 可执行、输入语料存在、输出目录不覆盖
[ -x "$TARGET" ] || { echo "target 不存在或不可执行: $TARGET" >&2; exit 1; }
[ -d "$INPUT_DIR" ] || { echo "输入语料目录不存在: $INPUT_DIR" >&2; exit 1; }
[ ! -e "$OUTPUT_DIR" ] || { echo "输出目录已存在，为避免覆盖请换 OUTPUT_DIR: $OUTPUT_DIR" >&2; exit 1; }

run_one() {  # $1 = 主/从标识
  local role="$1" args=(-i "$INPUT_DIR" -o "$OUTPUT_DIR" -m "$MEM_LIMIT" -t "$TIMEOUT_MS")
  [ -n "$DICT" ]        && args+=(-x "$DICT")
  [ "$RUN_SECONDS" != "0" ] && args+=(-V "$RUN_SECONDS")
  [ "$CMPLOG" = "1" ] && [ -x "$TARGET_CMPLOG" ] && args+=(-c "$TARGET_CMPLOG")
  [ "$role" = "master" ] && args+=(-M "master") || args+=(-S "slave_$role")
  args+=(-- "$TARGET" $TARGET_ARGS)
  echo "[run:$role] $AFL_BIN ${args[*]}"
  "$AFL_BIN" "${args[@]}"
}

if [ "$SLOTS" -le 1 ]; then
  run_one single
else
  run_one master &
  for ((i=1; i<SLOTS; i++)); do run_one "$i" & done
  wait
fi
```

宿主机需要时，再生成一层 `.bat` 包装：

```bat
@echo off
docker compose -f "<COMPOSE_FILE>" exec "<SERVICE>" bash -lc "bash <容器内脚本路径>"
```

## 5. 生成流程（每次执行）

1. **确认参数**：只问“这次变化的参数”，未提及的槽位沿用 §3 默认或上次已用值；留空的表意要与模板默认一致。
2. **保留基线**：环境导出与 wrapper 默认不动；仅替换槽位值。
3. **组命令**：按 §4 模板组装；`CMPLOG=1` 且 `TARGET_CMPLOG` 存在时才加 `-c`。
4. **写脚本**：生成到用户指定路径（默认 `<项目根>/tools/aflmy/run_<protocol>.sh` 或用户给的目录），带前置校验。
5. **预览确认**：把最终脚本与“相对上次命令的 diff”展示给用户，得到“可执行”确认后再实际运行；不擅自覆盖既有输出目录。

## 6. 进化规则（根据代码修改增量适配）

用户报告代码改动时，**在上一次已验证命令基础上做最小 diff**，只改受影响槽位：

| 代码改动 | 影响槽位 | 处理 |
|---|---|---|
| 改了 target 源码（server/example 等） | `TARGET`/`TARGET_CMPLOG` | 先按编译模板重编译（`cmake --build` 或 `make`），再 `ln -sfn` 更新软链接，fuzz 参数不动 |
| 新增/更换协议项目 | `PROTOCOL`/`TARGET`/`INPUT_DIR` | 用用户给的新路径，其余沿用 |
| 打开 sanitizer（ASan/UBSan） | 环境 | 编译/运行加 `AFL_USE_ASAN=1` / `AFL_USE_UBSAN=1`，`-m` 相应调大 |
| 改了输入契约（文件 vs stdin、格式） | `TARGET_ARGS` | 调整 `@@` 位置或改 stdin 模式 |
| 改了超时/预算 | `TIMEOUT_MS`/`RUN_SECONDS` | 改对应槽位 |
| 需要多实例并行 | `SLOTS` | `-M master` + 多个 `-S` |
| 改了 compose/容器 | `COMPOSE_FILE`/`SERVICE` | 改 wrapper |

**原则**：只改受影响的部分并明确列出 diff；其余保持上次值，保证“已验证正确”的基线不被动摇。

## 7. 校验与安全

- 生成脚本必须含 `test -x "$TARGET"`、输入目录存在、输出目录不覆盖三项前置校验。
- 不自动覆盖非空 `OUTPUT_DIR`；续跑已有会话用 `-i -`（resume）而非重开新输出目录，需用户明确要求。
- 不在脚本中写 API Key / 密码；环境变量注入即可。
- 实际执行前向用户展示最终命令并等待确认；涉及容器内高权限操作（如写 `/opt`）需用户授权。

## 8. 触发与默认行为

- **默认开启**：用户提供“测试正确”的命令、说“生成/调整启动脚本”“一键启动”“跑 fuzz”“多开几个实例”等即触发。
- 每次生成后回显：最终命令、相对上次命令的 diff、脚本保存路径、前置校验结果。

## 9. 已知参考（供 Agent 回溯）

- 编译命令整理（原始模板来源）：
  `E:\workspace\code\analysis\analysis-myafl-test\整理的build_commands\20260816_aflmy_slot1_regular_and_cmplog_build_commands.md`
- aflmy fuzz 调用样例：`E:\workspace\fuzzv1\aflmy\test\test-basic.sh`（`afl-fuzz -V07 -m <mem> -i in -o out -- <target>`）
- 可直接运行的示例产物（含「明文替换渠道」）：
  `E:\workspace\fuzzv1\.claude\skills\afl-launch-commander\examples\run_bacnet-stack.sh`
  生成新脚本时以它为准拷贝并只改「可手动修改」区域。
