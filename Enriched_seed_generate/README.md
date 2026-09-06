# Enriched Seed Generation

面向工业协议模糊测试的高质量初始种子生成工具。本项目组合协议格式、功能码/操作说明以及可选的历史 Issue 知识，生成结构有效、便于变异并适合 AFL 类工具使用的种子语料。

## 文档导航

- [快速开始](docs/handoff/01_QUICK_START.md)
- [当前状态](docs/handoff/02_CURRENT_STATUS.md)
- [项目结构](docs/handoff/03_PROJECT_STRUCTURE.md)
- [运行流程与操作手册](docs/handoff/04_OPERATION_GUIDE.md)
- [后续计划](docs/handoff/05_ROADMAP.md)
- [变更记录](docs/handoff/06_CHANGELOG.md)

## 核心流程

~~~text
raw_issue/*.txt
       |
       v
  SummIssue.py  --->  distilled_issue/*.txt
                            |
protocol_format/*.json -----+----- function_code/*/function.txt
                            |
                            v
                       Generate.py
                            |
                            v
                 high_quality_seeds/
                 |- issue_enhanced/
                 +- no_issue/
~~~

当前包含 BACnet、IEC 61850、IEC 60870、EtherNet/IP（OpENer）和 Modbus TCP 五组协议/项目资料及已生成种子。

## 最短运行示例

~~~powershell
python -m pip install "openai>=1.60.0"
$env:OPENAI_API_KEY = "<your-api-key>"
python Generate.py --format protocol_format/modbustcp.json --functions function_code/5.libmodbus/function.txt --issues distilled_issue/5.libmodbus --output generated_seeds/libmodbus-issue
~~~

不使用 Issue 增强时，去掉 --issues，并输出到独立的基线目录。

## 安全提示

- 不要提交 API Key；通过 OPENAI_API_KEY 和可选的 OPENAI_BASE_URL 注入配置。
- Generate.py 默认拒绝覆盖非空输出目录；重新生成时使用新目录。
- 历史 Issue 和 Payload 仅用于授权环境中的安全研究与回归测试。
