# PK × VK 种子生成消融：预注册

状态：实验前计划已归档；配置冻结和正式执行状态待填。

## 目标

评估工业协议模糊测试种子生成中协议知识（PK）与漏洞知识（VK）的独立作用，以及二者的互补或协同效应。

实验分为：

1. 首次独立 Replay：评价 LLM 原始种子的协议有效性、状态转换、漏洞相关性与风险区域可达性。
2. 24 小时 Fuzzing：评价初始优势能否转化为覆盖增长、风险探索和漏洞发现收益。

## 研究问题

- RQ1：PK 是否提高协议有效性和状态转换成功率？
- RQ2：VK 是否使种子更接近预定义风险目标？
- RQ3：PK 与 VK 是否存在互补或协同作用？
- RQ4：Replay 优势能否转化为 24 小时 Fuzzing 收益？

## 假设与预期

- H1：Full≈PK-only>VK-only≈Base，PK 主要提高 Validity、Parser Acceptance 和状态转换。
- H2：Full 与 VK-only 的 Risk Distance 更低、Closeness 更高。
- H3：Full 的 JVR/EVR 最高。
- H4：Full 的 Risk Coverage 更高、TTFRH 更短、Risk AUC 更大。

这些是预期结果，不是实际结论。全局 Edge Coverage 不预设 VK 组必须最高。

## 实验对象

bacnet-stack、OpENer、libiec61850、lib60870、libmodbus。

## 执行前冻结项

| 项目 | 当前记录 |
|---|---|
| 代码 Commit、Harness 版本 | 待填：记录可复现版本或 Hash |
| 编译器、Flags、Sanitizer、Instrumentation | 待填：正式运行前冻结 |
| 服务初始状态与复位方法 | 待填：描述快照或初始化过程 |
| LLM、API、生成参数 | 待填：四组必须一致 |
| 漏洞知识来源与版本 | 待填：按目标记录 |
| Vulnerability Card、Risk Targets | 待填：Replay 前冻结 |
| 显著性水平、最小实际效应 | 待填：查看正式结果前确定 |

## 结论边界

风险区域命中或 Crash 不等于已确认漏洞。漏洞必须稳定复现、最小化并按根因去重。
