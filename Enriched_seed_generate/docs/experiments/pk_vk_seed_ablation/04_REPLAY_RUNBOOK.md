# 首次独立 Replay 操作规程

## 目的

在不引入 Mutation、Queue Scheduling 或 Coverage-Guided Evolution 的条件下评价 LLM 原始种子。

~~~text
LLM Generation
-> Raw Seed
-> 恢复统一状态
-> Deterministic Replay
-> 收集 Validity、Transition、Trace 和 Risk Distance
~~~

## 前置条件

- 目标、Harness、Prompt 和生成预算已冻结。
- Vulnerability Card 与 Risk Targets 已冻结。
- Timeout、初始状态和复位方法一致。
- Trace、Handler 与状态采集已用确定性输入验证。

Harness 命令、容器、端口、快照和 Timeout 待填，因为实验计划未提供实际配置。

## 单 Seed 流程

1. 记录 Target、Configuration、Repetition、Seed ID 和 Hash。
2. 保留 Raw Seed，不预筛无效输入。
3. 恢复统一程序状态。
4. 以固定 Timeout 回放完整消息或序列。
5. 采集 Framing、Parser、Handler 和状态转换。
6. 保存 Functions、Blocks、Edges、Reach 和 Distance。
7. 保存 Crash、Hang、Sanitizer、耗时和返回状态。
8. 清理会话，避免影响下一 Seed。
9. 检查记录完整性。

## 禁止事项

- Mutation 或覆盖引导排队。
- 将 Replay 反馈送回后续 LLM 生成。
- 跨 Seed 保留会话状态。
- 按实验组改变 Timeout、复位或采集流程。
- Replay 前删除无效 Seed。

## 命令模板

~~~powershell
# 待填：恢复目标状态
<TBD_RESET_COMMAND>

# 待填：执行单 Seed/序列
<TBD_REPLAY_COMMAND> --target <target> --seed <path> --timeout <value>

# 待填：导出 Trace 与距离
<TBD_TRACE_EXPORT_COMMAND>
~~~

缺少核心标识、Configuration、执行状态或 Trace 状态的记录标为 Invalid。Parser 拒绝、无 Crash 或未命中风险目标是合法结果，不是实验无效。

## 产物

Raw Seed 清单及 Hash、Replay 记录、Trace/Coverage、异常原始证据、完整性报告和分组汇总。
