#!/bin/bash
# ============================================================
# 种子交接脚本（适配 Linux 项目结构）
# 功能：将 Enriched_seed_generate 生成的分类种子自动分发到项目
#       目标路径：<DEST_ROOT>/<对象名>/inputs/enriched_seeds/<类别>/
# ============================================================

set -euo pipefail

# ---------- 配置区域 ----------
# 源根目录：包含 base, full, pk_only, vk_only 等类别子目录
SRC_ROOT="/opt/tools/Enriched_seed_generate/diagnostic_20260906"

# 目标根目录：Linux 项目工作区根目录（包含各协议对象子目录）
DEST_ROOT="/opt/aflmy-test/1"

# 分发模式：link 或 copy
MODE="link"   # link = 符号链接，copy = 复制文件

# 四类种子目录名
SEED_CATEGORIES=("base" "full" "pk_only" "vk_only")

# 源对象名 -> 目标对象名 映射（可根据实际情况调整）
declare -A OBJ_MAP=(
    ["1.BACnet-stack"]="bacnet-stack"
    ["2.libiec61850"]="libiec61850"
    ["3.lib60870"]="lib60870"
    ["4.OpENer"]="OpENer"
    ["5.libmodbus"]="libmodbus"
)

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
    case $1 in
        --src) SRC_ROOT="$2"; shift 2 ;;
        --dest) DEST_ROOT="$2"; shift 2 ;;
        --mode) MODE="$2"; shift 2 ;;
        --help|-h)
            echo "用法: $0 [--src <源目录>] [--dest <目标目录>] [--mode link|copy]"
            exit 0
            ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ---------- 校验 ----------
if [[ ! -d "$SRC_ROOT" ]]; then
    echo "错误：源目录不存在: $SRC_ROOT"; exit 1
fi
if [[ ! -d "$DEST_ROOT" ]]; then
    echo "错误：目标根目录不存在: $DEST_ROOT"; exit 1
fi
if [[ "$MODE" != "link" && "$MODE" != "copy" ]]; then
    echo "错误：--mode 只能是 link 或 copy"; exit 1
fi

echo "=============================================="
echo "种子交接脚本启动"
echo "源目录: $SRC_ROOT"
echo "目标根目录: $DEST_ROOT"
echo "分发模式: $MODE"
echo "=============================================="

# 检测实际存在的种子类别
detected_categories=()
for cat in "${SEED_CATEGORIES[@]}"; do
    if [[ -d "$SRC_ROOT/$cat" ]]; then
        detected_categories+=("$cat")
    fi
done

if [[ ${#detected_categories[@]} -eq 0 ]]; then
    echo "错误：源目录下未找到任何种子类别"; exit 1
fi
echo "检测到种子类别: ${detected_categories[*]}"

# 遍历源对象目录（可能有些类别下缺失某些对象，脚本会跳过）
for src_obj in "${!OBJ_MAP[@]}"; do
    target_obj="${OBJ_MAP[$src_obj]}"
    echo ""
    echo "---------- 处理对象: $src_obj -> $target_obj ----------"

    # 目标基础目录：$DEST_ROOT/$target_obj/inputs/enriched_seeds
    target_enriched_dir="$DEST_ROOT/$target_obj/inputs/enriched_seeds"
    mkdir -p "$target_enriched_dir"

    for category in "${detected_categories[@]}"; do
        src_cat_obj="$SRC_ROOT/$category/$src_obj"
        if [[ ! -d "$src_cat_obj" ]]; then
            echo "  [跳过] $src_obj 不存在于 $category"
            continue
        fi

        # 目标类别目录
        dest_cat_dir="$target_enriched_dir/$category"
        mkdir -p "$dest_cat_dir"

        for sub in "afl_corpus" "sequences"; do
            src_sub="$src_cat_obj/$sub"
            if [[ ! -d "$src_sub" ]]; then
                echo "  [警告] $src_obj/$category/$sub 不存在，跳过"
                continue
            fi

            dest_sub="$dest_cat_dir/$sub"
            if [[ -e "$dest_sub" || -L "$dest_sub" ]]; then
                echo "  [警告] 目标已存在，覆盖: $dest_sub"
                rm -rf "$dest_sub"
            fi

            if [[ "$MODE" == "link" ]]; then
                ln -s "$src_sub" "$dest_sub"
                echo "  [链接] $src_obj/$category/$sub -> $dest_sub"
            else
                cp -r "$src_sub" "$dest_sub"
                echo "  [复制] $src_obj/$category/$sub -> $dest_sub"
            fi
        done
    done
    echo "  [完成] $target_obj 的种子已处理"
done

echo ""
echo "=============================================="
echo "种子交接完成！"
echo "示例目标路径: $DEST_ROOT/bacnet-stack/inputs/enriched_seeds/base/"
echo "=============================================="