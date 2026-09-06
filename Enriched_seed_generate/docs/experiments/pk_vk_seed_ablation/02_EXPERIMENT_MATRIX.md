# 实验矩阵与控制变量

## 2×2 因子设计

| 配置 | PK | VK | 定义 |
|---|---:|---:|---|
| Full（P+V+） | 是 | 是 | 同时提供结构化 PK/VK |
| PK-only（P+V−） | 是 | 否 | 仅提供 PK |
| VK-only（P−V+） | 否 | 是 | 仅提供 VK |
| Base（P−V−） | 否 | 否 | Generic-LLM 基线 |

P− 仍提供协议名称、输出格式、Harness 接口和单消息/序列要求，只是不提供字段结构、状态机、约束、校验关系和状态依赖。

## 计划规模

每个目标和配置生成 200 条 Raw Seeds，进行 3 次独立 Generation Repetition：

~~~text
5 × 4 × 200 × 3 = 12,000 raw seeds
~~~

Replay 使用全部 Raw Seeds，不预先删除无效输入，也不按 Accepted 数动态调整预算。

每个 Target/Configuration 至少进行 10 次独立 24 小时 Fuzzing：

~~~text
5 × 4 × 10 = 200 fuzzing runs
~~~

实际 CPU、并行度、运行日期和 Random Seed 列表待填。

## 控制变量

四组保持相同：

- LLM、模型/API 版本、Prompt Skeleton。
- Temperature、Top-p、Token 上限、调用次数、候选数和重试上限。
- 输出编码与序列化。
- 目标程序、Harness、Instrumentation、Sanitizer、Timeout。
- Fuzzer、Scheduler、Mutation、Dictionary、CPU、内存和核数。
- 运行时长、Crash 去重和漏洞确认规则。

除 PK/VK 模块外，提示词不得发生系统性变化。

## 实验单位

Replay 观察单位是 Raw Seed；生成重复单位是 Generation Repetition；Fuzzing 的统计重复单位是独立 Run；Target 应作为分层因素或随机效应。
