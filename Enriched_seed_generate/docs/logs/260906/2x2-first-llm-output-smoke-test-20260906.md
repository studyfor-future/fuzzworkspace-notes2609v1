# 2x2 first LLM output smoke test - 2026-09-06

## Scope

Protocol/project: Modbus TCP / 5.libmodbus.

This was a minimum-cost smoke test. Every factor cell used one candidate and
one final seed. The production upper limit remains 100.

Output root:

    high_quality_seedsv2/

## Commands

    conda run -n ICSTsys01-py39 python "Generate copy.py" --generation-channel base --protocol-name modbustcp --protocol-family modbus --final-seed-count 1 --candidate-count 1 --output "high_quality_seedsv2\base\5.libmodbus"

    conda run -n ICSTsys01-py39 python "Generate copy.py" --generation-channel vk-only --protocol-name modbustcp --issues "distilled_issue\5.libmodbus" --harness-input "stdin bytes" --sample-shape "message-sequence" --output-encoding "raw-binary-concat" --protocol-family modbus --final-seed-count 1 --candidate-count 1 --output "high_quality_seedsv2\vk_only\5.libmodbus"

    conda run -n ICSTsys01-py39 python "Generate copy.py" --generation-channel pk-only --format "protocol_format\modbustcp.json" --functions "function_code\5.libmodbus\function.txt" --final-seed-count 1 --candidate-count 1 --output "high_quality_seedsv2\pk_only\5.libmodbus"

    conda run -n ICSTsys01-py39 python "Generate copy.py" --generation-channel full --format "protocol_format\modbustcp.json" --functions "function_code\5.libmodbus\function.txt" --issues "distilled_issue\5.libmodbus" --final-seed-count 1 --candidate-count 1 --output "high_quality_seedsv2\full\5.libmodbus"

## Result matrix

| Mode | P | V | LLM/export | Sequence bytes | Frame bytes |
|---|---:|---:|---|---:|---|
| Base | - | - | PASS | 8 | 8 |
| VK-only | - | + | PASS | 21 | 7, 7, 7 |
| PK-only | + | - | PASS | 22 | 8, 8, 6 |
| Full | + | + | PASS | 6 | 6 |

All four outputs passed the following file-level checks:

- manifest.json parses as JSON.
- sequence.json parses as JSON.
- sequence.hex decodes to exactly the bytes in sequence.bin.
- The AFL corpus .bin file is byte-identical to sequence.bin.
- Per-message frame files are present.
- Existing high_quality_seeds content was not overwritten.

## Output layout

Each mode uses:

    high_quality_seedsv2/<mode>/5.libmodbus/
    |-- manifest.json
    |-- afl_corpus/
    |   +-- *.bin
    +-- sequences/
        +-- <seed-id>/
            |-- frames/
            |   +-- *.bin
            |-- sequence.bin
            |-- sequence.hex
            +-- sequence.json

## Protocol-structure finding

File export is correct, but the first generated Modbus messages are not
complete Modbus TCP requests/responses.

- Base produced an 8-byte Read Coils request containing MBAP plus function code
  but no start-address or quantity fields.
- VK-only produced three 7-byte frames. Their MBAP length fields claim more
  bytes than are present, and no complete PDU is available.
- PK-only produced two 8-byte frames missing function data and one 6-byte
  partial header.
- Full produced one 6-byte partial MBAP header with no unit identifier or PDU.

The internal review/validator accepted these outputs, so this is a protocol
validation and repair coverage gap rather than an export-format failure.

## Dependency note

The ICSTsys01-py39 environment initially lacked the OpenAI SDK. openai 2.48.0
was installed before running the real LLM tests.

## CLI note

The supported channel syntax is --generation-channel <mode>. A positional
command such as "Generate copy.py base ..." falls back to the legacy parser.
