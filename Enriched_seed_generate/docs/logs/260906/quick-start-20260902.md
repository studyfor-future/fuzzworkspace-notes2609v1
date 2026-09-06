# Quick Start

## 项目目录

```powershell
cd "D:\mycode\codex\analysis\tools\Enriched_seed_generate"
```

所有命令均使用 Anaconda 环境 `ICSTsys01-py39`。

## PK-only（P+V−）

使用协议格式和功能码知识，不使用漏洞 issue。

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --generation-channel pk-only `
  --format "<协议格式文件>" `
  --functions "<功能码文件>" `
  --final-seed-count 48 `
  --candidate-count 72 `
  --output "<输出目录>"
```

示例：

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --generation-channel pk-only `
  --format ".\protocol_format\libmodbus.txt" `
  --functions ".\function_code\libmodbus.txt" `
  --final-seed-count 48 `
  --candidate-count 72 `
  --output ".\output\libmodbus-pk-only"
```

## Full（P+V+）

同时使用协议知识和漏洞 issue。

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --generation-channel full `
  --format "<协议格式文件>" `
  --functions "<功能码文件>" `
  --issues "<漏洞 issue 目录>" `
  --final-seed-count 48 `
  --candidate-count 90 `
  --output "<输出目录>"
```

示例：

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --generation-channel full `
  --format ".\protocol_format\libmodbus.txt" `
  --functions ".\function_code\libmodbus.txt" `
  --issues ".\distilled_issue\5.libmodbus" `
  --final-seed-count 48 `
  --candidate-count 90 `
  --output ".\output\libmodbus-full"
```

## VK-only（P−V+）

不读取外部协议文档，使用漏洞 issue、模型内部协议先验和内置基础约束。

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --generation-channel vk-only `
  --protocol-name "libmodbus" `
  --issues ".\distilled_issue\5.libmodbus" `
  --harness-input "stdin bytes" `
  --sample-shape "message-sequence" `
  --output-encoding "raw-binary-concat" `
  --final-seed-count 48 `
  --candidate-count 72 `
  --output ".\output\libmodbus-vk-only"
```

## Base（P−V−）

不读取外部协议文档和漏洞 issue。

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --generation-channel base `
  --protocol-name "libmodbus" `
  --final-seed-count 48 `
  --candidate-count 72 `
  --output ".\output\libmodbus-base"
```

协议无法自动识别时可增加：

```powershell
--protocol-family modbus
```

可选值：`generic`、`modbus`、`bacnet`、`opener`、`iec60870`、`iec61850`。

## Legacy 兼容模式

保留原始调用逻辑和原始数量设置。

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" `
  --format "<协议格式文件>" `
  --functions "<功能码文件>" `
  --issues "<可选漏洞 issue 目录>" `
  --output "<输出目录>"
```

## 最大数量

PK-only、Full、VK-only 和 Base 的最终种子上限为 100，候选上限为 150。

```powershell
--final-seed-count 100 `
--candidate-count 150
```

候选数量必须大于或等于最终种子数量。

## 候选数量参数说明

### `ISSUE_CANDIDATE_COUNT`

`ISSUE_CANDIDATE_COUNT` 是旧 `legacy` 通道使用的程序内部常量，当前值为 18。

当 Legacy 使用 `--issues` 时，程序先规划和生成最多 18 个 issue 增强候选，再经过校验、审查和选择，最终仍按 Legacy 的 `FINAL_SEED_COUNT` 输出。

该常量只用于保留旧实验行为。显式选择 `pk-only`、`full`、`vk-only` 或 `base` 时，不使用这个常量。

### `--candidate-count`

`--candidate-count` 表示“候选种子池数量”，不是最终导出数量。

程序会按照该数量建立候选计划并调用模型生成候选，然后依次执行：

1. 十六进制和报文基础校验；
2. 协议基础修复；
3. 去重和历史 payload 碰撞检查；
4. 模型审查与必要的分批修订；
5. 多样性选择；
6. 从候选池中保留 `--final-seed-count` 个最终种子。

例如：

```powershell
--candidate-count 150 `
--final-seed-count 100
```

表示先生成和审查最多 150 个候选，最终选择并导出 100 个，而不是导出 150 个。

### 数量关系和影响

必须满足：

```text
1 <= final-seed-count <= 100
final-seed-count <= candidate-count <= 150
```

候选数量较大时：

- 更有机会覆盖不同操作、报文结构、长度、方向和状态序列；
- 校验或去重删除部分候选后，仍较容易达到最终数量；
- 模型 API 调用次数、运行时间和费用会相应增加。

当前推荐值：

| 通道 | `--final-seed-count` | `--candidate-count` |
|---|---:|---:|
| PK-only | 48 | 72 |
| Full | 48 | 90 |
| VK-only | 48 | 72 |
| Base | 48 | 72 |

需要构建最大规模语料库时使用 100/150；快速验证时可以使用 24/36。

