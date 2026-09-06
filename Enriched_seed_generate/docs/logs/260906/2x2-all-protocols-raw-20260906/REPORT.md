# All-protocol 2x2 raw LLM diagnostic report - 2026-09-06

## Scope

Five protocol projects, four P/V factor cells per project, four requested
candidate seeds and four requested final seeds per cell.

The validator in this report checks conservative outer-envelope and basic
request-size invariants. It is not a complete semantic protocol decoder.

## Aggregate result

- Test cells: 20
- Complete raw-response capture: 20/20
- Total LLM API calls captured: 79
- Cells exported: 16/20
- Exported cells with byte-consistent artifacts: 16/16
- Initial raw LLM batches containing basic protocol errors: 20/20
- Last normalized batches still containing errors: 7/20
- Exported final libraries containing errors: 6/20
- Final LLM reviews that accepted an invalid final library: 6

## Matrix

| Project | Mode | Calls | Raw invalid | Last normalized invalid | Final invalid | Export | Files | Diagnosis |
|---|---|---:|---:|---:|---:|---|---|---|
| 1.BACnet-stack | base | 5 | 5/5 | 0/5 | 0/5 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 1.BACnet-stack | vk_only | 5 | 4/4 | 0/2 | 0/0 | NO | N/A | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 1.BACnet-stack | pk_only | 4 | 74/74 | 10/15 | 10/15 | PASS | PASS | raw_llm_contains_invalid; invalid_survived_normalization |
| 1.BACnet-stack | full | 5 | 6/6 | 0/5 | 0/0 | NO | N/A | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 2.libiec61850 | base | 4 | 5/5 | 0/7 | 0/7 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 2.libiec61850 | vk_only | 7 | 3/4 | 0/4 | 0/4 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 2.libiec61850 | pk_only | 2 | 7/7 | 7/7 | 7/7 | PASS | PASS | raw_llm_contains_invalid; invalid_survived_normalization |
| 2.libiec61850 | full | 4 | 6/6 | 2/4 | 0/0 | NO | N/A | raw_llm_contains_invalid; invalid_survived_normalization |
| 3.lib60870 | base | 4 | 4/4 | 0/4 | 0/4 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 3.lib60870 | vk_only | 4 | 4/4 | 0/4 | 0/4 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 3.lib60870 | pk_only | 2 | 6/6 | 1/6 | 1/6 | PASS | PASS | raw_llm_contains_invalid; invalid_survived_normalization |
| 3.lib60870 | full | 4 | 6/6 | 0/7 | 0/6 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 4.OpENer | base | 4 | 6/6 | 6/6 | 6/6 | PASS | PASS | raw_llm_contains_invalid; invalid_survived_normalization |
| 4.OpENer | vk_only | 4 | 8/8 | 8/8 | 8/8 | PASS | PASS | raw_llm_contains_invalid; invalid_survived_normalization |
| 4.OpENer | pk_only | 5 | 1/7 | 0/6 | 0/0 | NO | N/A | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 4.OpENer | full | 5 | 6/6 | 0/7 | 0/7 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 5.libmodbus | base | 2 | 2/6 | 0/6 | 0/6 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 5.libmodbus | vk_only | 4 | 6/6 | 2/6 | 2/6 | PASS | PASS | raw_llm_contains_invalid; invalid_survived_normalization |
| 5.libmodbus | pk_only | 3 | 5/5 | 0/5 | 0/5 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |
| 5.libmodbus | full | 2 | 4/5 | 0/5 | 0/5 | PASS | PASS | raw_llm_contains_invalid; no_basic_envelope_error_after_last_normalization |

## Error propagation conclusion

For a cell marked raw_llm_contains_invalid, the first parsed model response
already contains a malformed or incomplete protocol envelope. When the same
cell is marked invalid_survived_normalization, normalize_candidate_library
and repair_protocol_message did not reject or fully repair it. If that cell
also exports invalid final messages, selection and the LLM review allowed the
error into the final corpus.

The exporter is assessed separately. A file consistency PASS means JSON
parsing succeeded and sequence.hex, sequence.bin, and the AFL corpus bytes
agree. It does not mean the protocol frame itself is valid.

## Per-cell examples

### 1.BACnet-stack / base

- base-plan-001 message 0, 8 bytes: BVLC length=12, actual=8; hex preview: 8100000c0004000c
- base-plan-002 message 0, 20 bytes: BVLC length=12, actual=20; hex preview: 8100000c0004000c000000010000000000000000

### 1.BACnet-stack / vk_only

- vk-plan-001-seed-001 message 0, 9 bytes: BVLC length=25, actual=9; hex preview: 810b001900ff0000ff
- vk-plan-002-seed-001 message 0, 9 bytes: BVLC length=5, actual=9; hex preview: 810a000500ff0000ff

### 1.BACnet-stack / pk_only

- bacnet-stack:protocol_format:bacnet-stack:format-overview:d904ae1e3d82 message 0, 4 bytes: BACnet/IP frame shorter than BVLC+NPDU minimum (4); hex preview: 000c0000
- bacnet-stack:protocol_format:bacnet-stack:format-overview:d904ae1e3d82 message 1, 2 bytes: BACnet/IP frame shorter than BVLC+NPDU minimum (2); hex preview: 0100

### 1.BACnet-stack / full

- 001 message 0, 18 bytes: BVLC length=2561, actual=18; hex preview: 81000a010000300e0000000e000000000000
- 002 message 0, 18 bytes: BVLC length=2561, actual=18; hex preview: 81000a010000300c0000000c000000000000

### 2.libiec61850 / base

- base-plan-001-seed-1 message 0, 16 bytes: TPKT length=22, actual=16; hex preview: 03000016030000000000000000010000
- base-plan-002-seed-1 message 0, 16 bytes: TPKT length=19, actual=16; hex preview: 03000013030000000000000000020000

### 2.libiec61850 / vk_only

- issue:590:590-summary:8f1dbbd54154 message 0, 19 bytes: TPKT length=20, actual=19; hex preview: 0300001402f000010000000001000600010000
- issue:573:573-summary:b7b57e9f1653 message 0, 16 bytes: TPKT length=12, actual=16; hex preview: 0300000c02f000010001000600010000

### 2.libiec61850 / pk_only

- baseline_valid message 0, 190 bytes: TPKT version/reserved bytes are not 03 00; TPKT length=0, actual=190; hex preview: 000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000
- stateful_valid message 0, 7 bytes: TPKT version/reserved bytes are not 03 00; TPKT length=0, actual=7; hex preview: 00030000000100

### 2.libiec61850 / full

- p001-1 message 0, 54 bytes: TPKT length=70, actual=54; hex preview: 0300004602f08001000100613730020100a030a02e020103ad2980010082248000a1201a1173696d706c65694f47656e
- p002-1 message 0, 30 bytes: TPKT length=24, actual=30; hex preview: 03000018030000f0c0110100000000000000000000000000000000000000

### 3.lib60870 / base

- baseline_valid-seed message 0, 8 bytes: APCI length=4, actual=6; hex preview: 6804680004000000
- function_code_coverage-seed message 0, 8 bytes: APCI length=4, actual=6; hex preview: 6804680004000000

### 3.lib60870 / vk_only

- ghsa-g3w7-x5rx-83xm message 0, 7 bytes: APCI length=4, actual=5; hex preview: 68040800000000
- ghsa-7v97-jmwv-w5j7 message 0, 7 bytes: APCI length=4, actual=5; hex preview: 68041300000000

### 3.lib60870 / pk_only

- plan-001-baseline-valid message 0, 291 bytes: APCI length=10, actual=289; hex preview: 680a00040000000068010000000000000000000000000000000000000000000000000000000000000000000000000000
- plan-002-stateful-valid message 0, 15 bytes: APCI length=4, actual=13; hex preview: 680401000000000068010000000100

### 3.lib60870 / full

- seedi message 0, 8 bytes: APCI length=4, actual=6; hex preview: 6804010000010000
- seedi message 1, 8 bytes: APCI length=5, actual=6; hex preview: 6805010000010000

### 4.OpENer / base

- base-plan-001 message 0, 4 bytes: EtherNet/IP encapsulation frame shorter than 24 bytes (4); hex preview: 00000000
- base-plan-002 message 0, 4 bytes: EtherNet/IP encapsulation frame shorter than 24 bytes (4); hex preview: 00000001

### 4.OpENer / vk_only

- vk-only-opener-314-001 message 0, 12 bytes: EtherNet/IP encapsulation frame shorter than 24 bytes (12); hex preview: 006500000000000000000000
- vk-only-opener-314-001 message 1, 14 bytes: EtherNet/IP encapsulation frame shorter than 24 bytes (14); hex preview: 0065000000000000000000000000

### 4.OpENer / pk_only

- seed-001 message 0, 154 bytes: encapsulation payload length=24931, actual=130; hex preview: 656e636170732064746d6f6e6e696e697a6174696f6e3d6f6e652e6c65746865726e65742e6f7267202f202d2d6c6973

### 4.OpENer / full

- s001 message 0, 32 bytes: encapsulation payload length=0, actual=8; hex preview: 0100000000000000000000000000000000000000000000000000000000000000
- s002 message 0, 32 bytes: encapsulation payload length=0, actual=8; hex preview: 0300000000000000000000000000000000000000000000000000000000000000

### 5.libmodbus / base

- b003-s001 message 1, 14 bytes: MBAP length=9, actual unit+PDU=8; hex preview: 0000000000090103000200010002
- b004-s001 message 1, 14 bytes: MBAP length=9, actual unit+PDU=8; hex preview: 0000000000090104000000010001

### 5.libmodbus / vk_only

- seed-279-001 message 0, 11 bytes: MBAP length=6, actual unit+PDU=5; function 0x01 request shorter than 12 bytes (11); hex preview: 000100000006ff01010000
- seed-279-001 message 1, 9 bytes: MBAP length=6, actual unit+PDU=3; hex preview: 000100000006ff0101

### 5.libmodbus / pk_only

- seed-001 message 0, 14 bytes: MBAP length=6, actual unit+PDU=8; hex preview: 0000000000060003000100000002
- seed-002 message 0, 14 bytes: MBAP length=6, actual unit+PDU=8; hex preview: 0000000000060006000100000001

### 5.libmodbus / full

- plan-002-stateful-001 message 0, 16 bytes: MBAP length=8, actual unit+PDU=10; hex preview: 00000000000800060000000200000000
- plan-002-stateful-001 message 1, 23 bytes: MBAP length=8, actual unit+PDU=17; hex preview: 0000000000080017000000020000000001000200000000

## Evidence locations

- Raw request/response captures: traces/<mode>/<project>/llm_calls/
- Normalization and final snapshots: traces/<mode>/<project>/stages/
- Machine-readable analysis: analysis.json
- Generated corpora: ../../../../../high_quality_seedsv2/diagnostic_20260906/

## Source integrity

Generate copy.py was not modified. The instrumented copy is
Generate diagnostic.py. Its baseline source SHA-256 before and after copying
was F1A8FB2FDA14458BF64A2E35B60AEAF611BA3E107720756BA09D7EF2BE398200.
