#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKBASE="${RUNNER_TEMP:-/tmp}/riskins-ci"
mkdir -p "$WORKBASE" "$WORKBASE/seeds"

AFL_ROOT="$ROOT"
export AFL_PATH="${AFL_PATH:-$AFL_ROOT}"
export PATH="$AFL_ROOT:$PATH"

IEC_ROOT="$ROOT/riskins_test/libiec61850-1.5.1"
IEC_BUILD="$IEC_ROOT/build"
MODBUS_ROOT="$ROOT/riskins_test/libmodbus-3.1.6"

pick_seed_dir() {
  for cand in "$@"; do
    if [[ -n "${cand:-}" && -d "$cand" ]] && find "$cand" -maxdepth 1 -type f | grep -q .; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

make_fallback_seed_dir() {
  local dst="$1"
  mkdir -p "$dst"
  printf 'A\n' > "$dst/seed_fallback"
  echo "$dst"
}

echo "[*] AFL_ROOT=$AFL_ROOT"
echo "[*] AFL_PATH=$AFL_PATH"

echo "[*] Build AFL++..."
pushd "$AFL_ROOT" >/dev/null
  make clean || true
  make all \
    DEBUG=1 \
    INTROSPECTION=1 \
    NO_NYX=1 \
    NO_QEMU=1 \
    NO_UNICORN=1 \
    NO_FRIDA=1 \
    LLVM_CONFIG="${LLVM_CONFIG:-llvm-config-18}" \
    -j"$(nproc)"
  test -x "$AFL_ROOT/afl-fuzz"
  test -x "$AFL_ROOT/afl-clang-fast"
popd >/dev/null

echo "[*] Build IEC61850 target..."
rm -rf "$IEC_BUILD"
mkdir -p "$IEC_BUILD"

IEC_TARGET=""
IEC_WORKDIR=""

if [[ -f "$IEC_ROOT/CMakeLists.txt" ]]; then
  set +e
  AFL_PATH="$AFL_PATH" cmake -S "$IEC_ROOT" -B "$IEC_BUILD" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_C_COMPILER="$AFL_ROOT/afl-clang-fast" \
    -DCMAKE_CXX_COMPILER="${CXX:-clang++-18}"
  cmake_rc=$?
  set -e

  if [[ $cmake_rc -eq 0 ]]; then
    cmake --build "$IEC_BUILD" -j"$(nproc)" || true
  else
    echo "[!] IEC CMake configure failed, will fall back to example Makefile build"
  fi
fi

if [[ -x "$IEC_BUILD/examples/server_example_basic_io/server_example_basic_io" ]]; then
  IEC_TARGET="$IEC_BUILD/examples/server_example_basic_io/server_example_basic_io"
  IEC_WORKDIR="$IEC_BUILD/examples/server_example_basic_io"
else
  pushd "$IEC_ROOT/examples/server_example_basic_io" >/dev/null
    make clean || true
    AFL_PATH="$AFL_PATH" make CC="$AFL_ROOT/afl-clang-fast" -j"$(nproc)"
    test -x "$IEC_ROOT/examples/server_example_basic_io/server_example_basic_io"
  popd >/dev/null
  IEC_TARGET="$IEC_ROOT/examples/server_example_basic_io/server_example_basic_io"
  IEC_WORKDIR="$IEC_ROOT/examples/server_example_basic_io"
fi

chmod +x "$IEC_TARGET" || true

echo "[*] Build libmodbus target..."
chmod +x "$MODBUS_ROOT/autogen.sh" || true
find "$MODBUS_ROOT" -maxdepth 1 -type f \( \
  -name configure -o \
  -name config.guess -o \
  -name config.sub -o \
  -name install-sh -o \
  -name missing -o \
  -name depcomp -o \
  -name ltmain.sh \
\) -exec chmod +x {} + || true

pushd "$MODBUS_ROOT" >/dev/null
  ./autogen.sh
  make distclean || true
  AFL_PATH="$AFL_PATH" CC="$AFL_ROOT/afl-clang-fast" CFLAGS="-O2 -g" ./configure --disable-shared --enable-static
  make -j"$(nproc)"
  test -x "$MODBUS_ROOT/tests/unit-test-server"
popd >/dev/null

MODBUS_TARGET="$MODBUS_ROOT/tests/unit-test-server"
MODBUS_WORKDIR="$MODBUS_ROOT/tests"
chmod +x "$MODBUS_TARGET" || true

echo "[*] Prepare seed directories..."
IEC_SEEDS="$(pick_seed_dir \
  "$IEC_BUILD/examples/server_example_basic_io/inputs/seed_bin_origin" \
  "$IEC_ROOT/examples/server_example_basic_io/inputs/seed_bin_origin" \
  "$IEC_BUILD/examples/server_example_basic_io/inputs" \
  "$IEC_ROOT/examples/server_example_basic_io/inputs" \
  || true)"

if [[ -z "$IEC_SEEDS" ]]; then
  IEC_SEEDS="$(make_fallback_seed_dir "$WORKBASE/seeds/iec61850")"
fi

MODBUS_SEEDS="$(pick_seed_dir \
  "$MODBUS_ROOT/tests/inputs/seed_bin_origin" \
  "$MODBUS_ROOT/tests/inputs" \
  "$MODBUS_ROOT/inputs/seed_bin_origin" \
  "$MODBUS_ROOT/inputs" \
  || true)"

if [[ -z "$MODBUS_SEEDS" ]]; then
  MODBUS_SEEDS="$(make_fallback_seed_dir "$WORKBASE/seeds/modbus")"
fi

echo "[*] IEC target     : $IEC_TARGET"
echo "[*] IEC workdir    : $IEC_WORKDIR"
echo "[*] IEC seeds      : $IEC_SEEDS"
echo "[*] Modbus target  : $MODBUS_TARGET"
echo "[*] Modbus workdir : $MODBUS_WORKDIR"
echo "[*] Modbus seeds   : $MODBUS_SEEDS"

{
  echo "RISKINS_WORKBASE=$WORKBASE"
  echo "AFL_ROOT=$AFL_ROOT"
  echo "AFL_PATH=$AFL_PATH"
  echo "IEC_TARGET=$IEC_TARGET"
  echo "IEC_WORKDIR=$IEC_WORKDIR"
  echo "IEC_SEEDS=$IEC_SEEDS"
  echo "MODBUS_TARGET=$MODBUS_TARGET"
  echo "MODBUS_WORKDIR=$MODBUS_WORKDIR"
  echo "MODBUS_SEEDS=$MODBUS_SEEDS"
} >> "$GITHUB_ENV"

echo "[*] Build finished."