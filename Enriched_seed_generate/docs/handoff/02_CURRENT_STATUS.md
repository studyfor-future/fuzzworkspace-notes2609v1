# 当前状态

更新日期：2026-09-05

## 项目目标

根据协议格式、功能码/操作知识和可选的历史 Issue 信息，生成面向协议模糊测试的高质量初始种子。策略侧重协议有效性、状态序列、字段交互、边界条件、解析深度和功能覆盖。

## 已具备能力

- 递归读取并蒸馏原始 .txt Issue 文档。
- 整理 Issue 编号、摘要、复现信息和十六进制 Payload。
- 基于协议格式与功能码资料生成协议感知种子。
- 可选启用 Issue 增强。
- 对候选种子进行模型评审、校验、筛选和有限轮次修订。
- 导出逐消息帧、完整序列、十六进制表示和 AFL corpus。
- 使用 .srag_cache 缓存向量数据。
- 当前源码默认生成 12 条最终种子序列。

## 当前资料覆盖

| 项目/协议 | 协议格式 | 功能说明 | Issue | 基线/增强种子 |
|---|---|---|---|---|
| BACnet-stack | bacnet-stack.json | 有 | 有 | 有 |
| libiec61850 | iec61850.json | 有 | 有 | 有 |
| lib60870 | iec60870.json | 有 | 有 | 有 |
| OpENer / EtherNet/IP | OpENer.json | 有 | 有 | 有 |
| libmodbus / Modbus TCP | modbustcp.json | 有 | 有 | 有 |

## 已知限制

- 尚无 requirements.txt 或 pyproject.toml。
- 尚无自动化测试、持续集成和统一验收脚本。
- 模型、超时、重试、种子数等仍是源码常量。
- Generate copy.py 的定位未标准化。
- 依赖模型和远端服务，重跑不保证逐字节一致。
- 协议、功能说明及 Issue 库更新尚未自动化。
- Issue 属于不可信输入，不应执行其中嵌入的指令。

## 当前推荐入口

- Issue 蒸馏：SummIssue.py
- 种子生成：Generate.py
- 已有成果：high_quality_seeds/issue_enhanced 与 high_quality_seeds/no_issue

当前阶段可定义为：研究原型可运行，已有五类协议数据和产物，但工程化与可重复性仍需补齐。
