# 快速开始

## 1. 运行环境

建议使用 Python 3.9 或更高版本、openai 1.60.0 或更高版本，以及有效的 OPENAI_API_KEY。

~~~powershell
Set-Location D:\mycode\codex\analysis\tools\Enriched_seed_generate
conda activate ICSTsys01-py39
python --version
python -m pip install "openai>=1.60.0"
$env:OPENAI_API_KEY = "<your-api-key>"
# 使用兼容服务时可选：
# $env:OPENAI_BASE_URL = "https://example.invalid/v1"
~~~

不要把真实密钥写进脚本、README 或提交记录。

## 2. 查看帮助

~~~powershell
python SummIssue.py --help
python Generate.py --help
~~~

## 3. 蒸馏 Issue

~~~powershell
python SummIssue.py -i raw_issue -o distilled_issue_staging
~~~

建议先输出到新目录，人工检查后再合并到 distilled_issue。脚本递归处理 .txt 文件并保留相对目录；已有同名输出会被跳过。

## 4. 生成种子

Issue 增强模式：

~~~powershell
python Generate.py --format protocol_format/modbustcp.json --functions function_code/5.libmodbus/function.txt --issues distilled_issue/5.libmodbus --output generated_seeds/libmodbus-issue
~~~

基线模式：

~~~powershell
python Generate.py --format protocol_format/modbustcp.json --functions function_code/5.libmodbus/function.txt --output generated_seeds/libmodbus-baseline
~~~

## 5. 验收

1. 命令退出码为 0。
2. 输出目录含 afl_corpus 和 sequences。
3. afl_corpus 中存在非空 .bin 文件。
4. 每个序列目录中有 sequence.bin、sequence.hex、帧文件和清单信息。
5. 重复运行时使用新输出目录。

## 6. 常见问题

- No API key found：设置 OPENAI_API_KEY，必要时设置 OPENAI_BASE_URL。
- 缺少 SDK：运行 python -m pip install "openai>=1.60.0"。
- 找不到输入：确认当前目录或改用绝对路径。
- 输出目录非空：换一个新目录。
- 找不到 Issue：确认 --issues 指向含 .txt 或 .json 文档的目录。
