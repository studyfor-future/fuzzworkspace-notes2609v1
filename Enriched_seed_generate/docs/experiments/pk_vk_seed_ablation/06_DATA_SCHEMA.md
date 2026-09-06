# 数据 Schema

实际存储格式、字段长度和数据库实现待项目落地时确定。以下是实验计划要求的最小字段。

## 通用标识

| 字段 | 类型 | 说明 |
|---|---|---|
| experiment_id | string | 固定实验标识 |
| target | enum | 五个实验对象之一 |
| configuration | enum | Full、PK-only、VK-only、Base |
| code_version | string | Commit 或等价版本 |
| harness_version | string | Harness 版本/Hash |
| prompt_hash | string | 对应 Prompt Hash |
| corpus_hash | string | Corpus 内容 Hash |

## Replay

| 字段 | 类型 | 规则 |
|---|---|---|
| generation_repetition | integer | 计划为 1—3 |
| seed_id、seed_hash | string | 实验内唯一；按完整输入计算 Hash |
| replay_success | boolean | Harness 是否完成回放 |
| framing_valid | boolean | 自动判定 |
| parser_accepted | boolean | 自动判定 |
| intended_handler_reached | boolean | 自动判定 |
| attempted_transitions | integer | 无状态协议可为 0 |
| successful_transitions | integer | 不大于尝试数 |
| sequence_completed | boolean/null | 无状态协议可为 null |
| vulnerability_relevance_score | integer | 0、1、2 |
| relevance_evidence | string/list | 字段、状态、操作与证据 |
| functions_hit、basic_blocks_hit、edges_hit | list | 动态 Trace |
| risk_region_hit | boolean/null | 未配置动态目标时为 null |
| nearest_risk_target | string/null | 最近目标 |
| risk_distance、closeness | number/null | 截断值待填 |
| crash、hang | boolean | 原始事件 |
| sanitizer_report | string/null | 报告引用或签名 |
| execution_time_ms | number | 毫秒 |
| return_status | string | Exit/Signal/Harness 状态 |
| record_validity | enum | Valid、Invalid、Valid-with-warning |
| invalid_or_warning_reason | string/null | 非 Valid 时必填 |

## Fuzzing Run

| 字段 | 类型 | 说明 |
|---|---|---|
| run_id | string | 独立 Run 唯一标识 |
| setting | enum | Raw-budget、Valid-corpus |
| fuzzer_random_seed | string/integer | 预先冻结 |
| start_time、end_time | datetime | 时区待填 |
| planned_duration_hours | number | 计划为 24 |
| actual_duration_seconds | number | 实际时长 |
| total_executions | integer | 累计执行 |
| median_execs_per_second | number | 全程中位吞吐量 |
| run_validity | enum | Valid、Invalid、Valid-with-warning |
| invalid_or_warning_reason | string/null | 判定依据 |

## 时间序列

保存 run_id、elapsed_seconds、total_executions、occupied_bitmap_slots、unique_edges、risk_targets_hit、risk_region_coverage、minimum_risk_distance、risk_closeness、unique_risk_paths、crashes、hangs、sanitizer_findings、confirmed_vulnerabilities。

## 建议文件

~~~text
manifest.json
raw_seed_inventory.csv
replay_records.csv
fuzzing_runs.csv
fuzzing_timeseries.csv
relevance_labels.csv
confirmed_vulnerabilities.csv
deviations.md
~~~

CSV 方言、空值编码、Hash 算法、时区、ID 规则和 JSON Schema 待填；原计划没有指定这些实现细节。
