# 运行流程与操作手册

## 总体流程

~~~text
收集原始 Issue
  -> 蒸馏并人工抽查
  -> 选择协议格式与功能说明
  -> 分别运行基线和 Issue 增强生成
  -> 校验产物
  -> 送入授权的 fuzzing 环境
  -> 记录实验配置和结果
~~~

## 一、Issue 蒸馏

~~~powershell
python SummIssue.py -i raw_issue -o distilled_issue_staging
~~~

规则：

- 递归发现 .txt 并保留相对目录。
- 输入与输出必须不同且不能互相嵌套。
- 已有同名输出会跳过。
- 单文件失败时记录错误并继续。
- 完成后输出 processed、skipped 和 failed。

人工抽查编号、摘要、复现信息和 Payload，避免把原文中的命令当作可信指令。

## 二、种子生成

Issue 增强：

~~~powershell
python Generate.py --format protocol_format/bacnet-stack.json --functions function_code/1.BACnet-stack/function.txt --issues distilled_issue/1.BACnet-stack --output generated_seeds/bacnet-issue-20260905
~~~

基线：

~~~powershell
python Generate.py --format protocol_format/bacnet-stack.json --functions function_code/1.BACnet-stack/function.txt --output generated_seeds/bacnet-baseline-20260905
~~~

基线与增强实验必须使用不同输出目录。

## 三、参数

| 参数 | 必需 | 含义 |
|---|---:|---|
| --format | 是 | 协议格式 JSON |
| --functions | 是 | 功能码或操作说明 |
| --issues | 否 | 蒸馏 Issue .txt/.json 目录；省略即基线模式 |
| --output | 是 | 独立输出目录 |

## 四、输出使用

- afl_corpus/*.bin：AFL/AFL++ 初始语料。
- sequences/*/sequence.bin：完整消息序列。
- sequences/*/sequence.hex：人工审阅版本。
- sequences/*/frames/*.bin：拆分的消息帧。
- 清单和元数据：追踪证据、模型、编码、哈希与评审信息。

当前序列编码为 concat。若 harness 需要长度前缀或会话边界，接入时必须转换。

## 五、运行前后检查

运行前确认输入映射、环境变量、空输出目录和 Issue 目录。运行后确认退出码为 0、二进制非空、十六进制合法、清单合理，并保存命令、时间、输入版本和输出位置。

## 六、失败处理

1. 保留日志和未完成输出。
2. 区分输入、依赖、API、结构化输出和本地校验错误。
3. 暂时性 API 错误可换新目录重试。
4. 数据问题先修复输入。
5. 替换正式种子库时更新变更记录。
