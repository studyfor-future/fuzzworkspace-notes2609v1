#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 /path/to/target [args...]" >&2
  exit 2
fi

: "${PREENY_DIR:?PREENY_DIR is required}"
TARGET_TIMEOUT="${TARGET_TIMEOUT:-2s}"
TARGET_WORKDIR="${TARGET_WORKDIR:-$(pwd)}"
PREENY_SOCKET_SO="${PREENY_SOCKET_SO:-desock.so}"

TARGET="$1"
shift || true

chmod +x "$TARGET" || true
cd "$TARGET_WORKDIR"

preloads=()

for so in \
  "$PREENY_DIR/$PREENY_SOCKET_SO" \
  "$PREENY_DIR/dealarm.so" \
  "$PREENY_DIR/desleep.so" \
  "$PREENY_DIR/defork.so"
do
  if [[ -f "$so" ]]; then
    preloads+=("$so")
  fi
done

if [[ ${#preloads[@]} -eq 0 ]]; then
  echo "no usable preeny preload library found under: $PREENY_DIR" >&2
  exit 2
fi

export LD_PRELOAD="$(IFS=:; echo "${preloads[*]}")${LD_PRELOAD:+:$LD_PRELOAD}"

set +e
timeout -s TERM "$TARGET_TIMEOUT" "$TARGET" "$@" >/dev/null 2>&1
st=$?
set -e

case "$st" in
  0|124|137|143)
    exit 0
    ;;
  *)
    exit "$st"
    ;;
esac