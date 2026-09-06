# 24 小时 Fuzzing 操作规程

## 两种设置

Raw-Budget Setting 使用等量 Raw LLM Seeds，保留无效输入成本，是主实验。

Valid-Corpus Setting 从各组抽取等量 Valid Seeds，用于隔离 VK 的下游贡献。抽样数量和 Random Seed 待填并须预先冻结。

## 固定条件

目标代码、Harness、Instrumentation、Sanitizer、Fuzzer、Scheduler、Mutation、Dictionary、CPU、内存、核数、Timeout、24 小时时长、Crash 去重和日志规则均保持一致。

每个 Target/Configuration 至少 10 个独立 Run，每个 Run 使用预先固定且不同的 Fuzzer Random Seed。

## 单次 Run

1. 选择 Target、Configuration、Setting、Run ID 和 Random Seed。
2. 清理残留进程、端口、共享内存和状态。
3. 校验二进制、配置和 Corpus Hash。
4. 保存环境、代码、Prompt、Corpus 与 Risk Targets。
5. 启动目标和 Fuzzer。
6. 按固定周期采集时间序列。
7. 运行 24 小时或至预定义停止条件。
8. 保存 Queue、Crashes、Hangs、日志和最终配置。
9. 完整性检查并标记 Valid、Invalid 或 Valid-with-warning。

## 待填命令

~~~powershell
<TBD_PRE_RUN_CLEANUP_COMMAND>
<TBD_START_TARGET_COMMAND>
<TBD_START_FUZZER_COMMAND>
<TBD_COLLECT_METRICS_COMMAND>
<TBD_STOP_AND_ARCHIVE_COMMAND>
~~~

原计划建议每 10 或 30 分钟采样。正式运行前须二选一并冻结：

~~~text
sampling_interval = 待填：10 min 或 30 min
~~~

记录 Bitmap、Edges/Blocks、Risk Targets、Risk Coverage、最小距离、Unique Risk Paths、Crashes、Hangs、Sanitizer 和 Confirmed Vulnerabilities。

不得只保留 24 小时终点。TTFRH 未命中的 Run 按右删失，不能赋值为 24 小时后参与普通均值。保存完整曲线以计算 AUC。

漏洞需经过异常去重、稳定复现、输入最小化、根因定位、同根因合并及 Card 关系确认；最终报告 Unique Confirmed Vulnerabilities。
