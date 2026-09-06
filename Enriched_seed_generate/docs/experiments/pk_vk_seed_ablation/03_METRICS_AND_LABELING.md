# 指标与标注规则

所有比例指标以原始生成种子数 N_raw 为分母，不能改用筛选后的 Accepted Seeds。

## Replay 指标

### Protocol Validity（V）

Seed 必须能够回放，通过 Framing、长度、类型和校验检查，未被通用格式检查立即拒绝，到达 Intended Handler；状态型协议还须完成必要前置交互。

~~~text
V = Valid Seeds / N_raw
~~~

只通过 Framing 但未到 Handler 可记为 Syntactically Valid，不计入完整 V。

### 状态转换

~~~text
STSR = Sum(Successful Transitions) / Sum(Attempted Transitions)
Sequence Success = Completed Required Sequences / N_raw
~~~

无状态协议记为 N/A，不填写 100%。

### Vulnerability Relevance（R）

Vulnerability Card 应预先冻结组件/函数、消息类型、敏感字段、所需状态、触发操作、边界条件和证据。

| 分值 | 判定 |
|---:|---|
| 0 | 一般协议消息，与目标漏洞无关 |
| 1 | 仅关键词、消息类型或组件相关 |
| 2 | 明确操纵相关字段、状态或触发条件，且无明显矛盾 |

只有 2 分计为 Relevant。

~~~text
R = Relevant Seeds / N_raw
JVR = Valid AND Relevant / N_raw
EVR = Valid AND Relevant AND Reach / N_raw
~~~

JVR 必须直接计算联合事件，不能以 V×R 代替。只有存在动态 Trace 和冻结的 Risk Targets 时使用 EVR，否则只报告 JVR。

### Risk Distance

~~~text
D_i = Trace 到 Risk Targets 的最短 CFG/Call-Graph 距离
Closeness_i = 1 / (1 + D_i)
~~~

命中时 D=0。无 Trace 或不可达时使用预先确定的 D_max+1。跨目标比较使用标准化距离、排名或 Closeness。

## Fuzzing 指标

- RH@24h：24 小时内命中的 Risk Targets 比例。
- Bitmap：固定大小和哈希方案下的 Occupied Slots。
- EdgeCov@24h：24 小时 Unique Edges。
- TTFRH：首次风险命中时间；未命中按右删失。
- AUC：Edge、Risk Coverage 和 Risk Closeness 曲线面积。
- Confirmed Vulnerabilities：稳定复现、最小化并按根因去重后的漏洞。

## 标注流程

自动规则判定执行类指标；独立评估模型依据固定 Card 和 Rubric 盲法粗筛；两名研究者复核，分歧由第三人裁决。评估模型不得知道实验组和预期排序。

标注者、评估模型/Prompt Hash、抽样比例及 Cohen’s Kappa 或 Krippendorff’s Alpha 待填；若只复核抽样，还需报告 AI 的 Precision、Recall 和 F1。
