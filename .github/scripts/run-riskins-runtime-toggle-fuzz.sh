#!/usr/bin/env bash
set -euo pipefail

: "${RISKINS_WORKBASE:?}"
: "${AFL_ROOT:?}"
: "${IEC_TARGET:?}"
: "${IEC_WORKDIR:?}"
: "${IEC_SEEDS:?}"
: "${MODBUS_TARGET:?}"
: "${MODBUS_WORKDIR:?}"
: "${MODBUS_SEEDS:?}"
: "${PREENY_DIR:?}"

export AFL_PATH="${AFL_PATH:-$AFL_ROOT}"
export PATH="$AFL_ROOT:$PATH"

OUT_ROOT="$RISKINS_WORKBASE/fuzz-out"
FUZZ_SECONDS="${FUZZ_SECONDS:-10800}"
PREENY_SO="${PREENY_DIR}/${PREENY_SOCKET_SO:-desock.so}"

test -x "$AFL_ROOT/afl-fuzz"
test -f "$PREENY_SO"
test -x "$IEC_TARGET"
test -x "$MODBUS_TARGET"

rm -rf "$OUT_ROOT"
mkdir -p "$OUT_ROOT"

declare -a pids=()
declare -a names=()

launch_case() {
  local name="$1"
  local mode="$2"      # risk-on | risk-off
  local target="$3"
  local seeds="$4"
  local workdir="$5"
  local runtime_dir="$OUT_ROOT/runtime-$name"
  local target_name

  target_name="$(basename "$target")"

  mkdir -p "$OUT_ROOT/$name"
  rm -rf "$runtime_dir"
  mkdir -p "$runtime_dir"
  cp -a "$workdir"/. "$runtime_dir"/

  if [[ ! -x "$runtime_dir/$target_name" ]]; then
    chmod +x "$runtime_dir/$target_name" || true
  fi

  echo "[*] launching $name ($mode)"
  (
    cd "$runtime_dir"

    if [[ "$mode" == "risk-off" ]]; then
      env \
        AFL_PATH="$AFL_PATH" \
        LD_PRELOAD="$PREENY_SO" \
        AFL_DISABLE_RISK=1 \
        AFL_DISABLE_RISK_SCHED=1 \
        AFL_SKIP_CPUFREQ="${AFL_SKIP_CPUFREQ:-1}" \
        AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES="${AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES:-1}" \
        AFL_NO_UI="${AFL_NO_UI:-1}" \
        AFL_NO_AFFINITY="${AFL_NO_AFFINITY:-1}" \
        AFL_QUIET="${AFL_QUIET:-1}" \
        "$AFL_ROOT/afl-fuzz" \
          -V "$FUZZ_SECONDS" \
          -m none \
          -t 2000+ \
          -i "$seeds" \
          -o "$OUT_ROOT/$name" \
          -- "./$target_name"
    else
      env \
        AFL_PATH="$AFL_PATH" \
        LD_PRELOAD="$PREENY_SO" \
        AFL_SKIP_CPUFREQ="${AFL_SKIP_CPUFREQ:-1}" \
        AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES="${AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES:-1}" \
        AFL_NO_UI="${AFL_NO_UI:-1}" \
        AFL_NO_AFFINITY="${AFL_NO_AFFINITY:-1}" \
        AFL_QUIET="${AFL_QUIET:-1}" \
        "$AFL_ROOT/afl-fuzz" \
          -V "$FUZZ_SECONDS" \
          -m none \
          -t 2000+ \
          -i "$seeds" \
          -o "$OUT_ROOT/$name" \
          -- "./$target_name"
    fi
  ) >"$OUT_ROOT/$name.console.log" 2>&1 &

  pids+=("$!")
  names+=("$name")
}

launch_case "iec61850-risk-on"  "risk-on"  "$IEC_TARGET"    "$IEC_SEEDS"    "$IEC_WORKDIR"
launch_case "iec61850-risk-off" "risk-off" "$IEC_TARGET"    "$IEC_SEEDS"    "$IEC_WORKDIR"
launch_case "modbus-risk-on"    "risk-on"  "$MODBUS_TARGET" "$MODBUS_SEEDS" "$MODBUS_WORKDIR"
launch_case "modbus-risk-off"   "risk-off" "$MODBUS_TARGET" "$MODBUS_SEEDS" "$MODBUS_WORKDIR"

status=0
for i in "${!pids[@]}"; do
  if ! wait "${pids[$i]}"; then
    echo "[!] campaign failed: ${names[$i]}" >&2
    status=1
  else
    echo "[+] campaign finished: ${names[$i]}"
  fi
done

exit "$status"