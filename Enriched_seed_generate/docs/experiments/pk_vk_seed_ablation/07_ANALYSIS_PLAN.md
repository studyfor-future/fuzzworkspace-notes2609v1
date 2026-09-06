# 统计分析计划

## 因子效应

这是 2×2 因子设计，必须估计 PK 主效应、VK 主效应和 PK×VK 交互，不能只比较 Full 与 Base。

对于越大越好的指标 Y：

~~~text
Effect_PK = (Y_Full + Y_PK-only)/2 - (Y_VK-only + Y_Base)/2
Effect_VK = (Y_Full + Y_VK-only)/2 - (Y_PK-only + Y_Base)/2
Interaction = (Y_Full - Y_PK-only) - (Y_VK-only - Y_Base)
~~~

Distance 和 TTFRH 越小越好，解释时反转方向，或改用 Closeness/速度指标。

## 分析层级

- 每个 Target 分别报告四组结果。
- Generation Repetition 和 Fuzzing Run 保持为独立重复。
- Target 与 Generation/Run Repetition 作为随机效应或分层因素。
- 不将同一 Target 内的 Seed 当作完全独立的科研重复。
- 跨 Target 使用标准化指标、宏平均、分层模型或适当效应量。

## 方法

| 数据 | 计划方法 |
|---|---|
| Seed-Level 二元指标 | 混合效应 Logistic Regression 或 Target 分层 Bootstrap |
| Coverage、AUC、Bitmap | Median、IQR、Bootstrap 95% CI |
| TTFRH | Kaplan-Meier、Log-rank 或 Cox Model |
| Confirmed Vulnerabilities | 描述统计及 Poisson/Negative-Binomial 模型 |
| 多重比较 | Holm Correction |

同时报告效应量和置信区间，不能只报告 p 值。

## 判定关系

- PK：Validity、STSR、Sequence Success 的正向主效应。
- VK：更低 Risk Distance、更高 Relevance/Closeness、更短 TTFRH。
- 协同：Full 在 JVR、EVR、Risk AUC 或 RH@24h 最佳，且交互项为正。
- 持续性：Replay 优势能在 24 小时曲线中保持。

VK 提升风险覆盖但降低全局 Edge Coverage，不直接判为无效；PK 只提升 Validity 可解释为协议可执行性贡献；Full 的早期优势后期消失，可能表明 Mutation 抵消初始差异；漏洞数无差异可能受漏洞稀缺和统计功效影响。

## 查看结果前待填

显著性水平、最小实际效应、Bootstrap 次数、模型公式、Cox 协变量、Planned Contrasts、缺失/异常处理、敏感性分析、跨 Target 汇总方法及统计软件版本。
