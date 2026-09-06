# 项目结构

~~~text
Enriched_seed_generate/
|- README.md
|- Generate.py                  # 正式种子生成入口
|- Generate copy.py             # 历史/实验副本
|- SummIssue.py                 # Issue 蒸馏入口
|- protocol_format/             # 协议格式 JSON
|- function_code/               # 功能码/操作说明
|- raw_issue/                   # 原始 Issue
|- distilled_issue/             # 蒸馏 Issue
|- high_quality_seeds/
|  |- issue_enhanced/
|  +- no_issue/
+- docs/handoff/                # 交接文档
~~~

## 核心脚本

SummIssue.py 递归处理 .txt Issue，输出编号、摘要、复现信息和规范化 Payload；采用非覆盖式写入。

~~~text
python SummIssue.py -i INPUT_DIR -o OUTPUT_DIR
~~~

Generate.py 加载协议格式、功能说明和可选 Issue，经规划、生成、评审、校验和筛选后导出种子。

~~~text
python Generate.py --format FILE --functions FILE [--issues DIR] --output DIR
~~~

## 输出结构

~~~text
<output>/
|- afl_corpus/
|  +- NNN-<seed_id>.bin
+- sequences/
   +- NNN-<seed_id>/
      |- frames/*.bin
      |- sequence.bin
      |- sequence.hex
      +- 清单与元数据
~~~

## 项目与输入映射

| 项目 | 格式文件 | 功能说明 | Issue 目录 |
|---|---|---|---|
| bacnet-stack | protocol_format/bacnet-stack.json | function_code/1.BACnet-stack/function.txt | distilled_issue/1.BACnet-stack |
| libiec61850 | protocol_format/iec61850.json | function_code/2.libiec61850/function.txt | distilled_issue/2.libiec61850 |
| lib60870 | protocol_format/iec60870.json | function_code/3.lib60870/function.txt | distilled_issue/3.lib60870 |
| OpENer | protocol_format/OpENer.json | function_code/4.OpENer/function.txt | distilled_issue/4.OpENer |
| libmodbus | protocol_format/modbustcp.json | function_code/5.libmodbus/function.txt | distilled_issue/5.libmodbus |
