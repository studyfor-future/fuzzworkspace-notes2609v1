# Count-65 all-protocol 2x2 diagnostic report

## Configuration

- Five projects and four P/V factor cells per project; 20 cells total.
- candidate-count = 65 and final-seed-count = 65 for every cell.
- Maximum requested final seeds: 1,300.
- Separate output root: high_quality_seedsv2/diagnostic_count65_20260906.

## Aggregate result

- Terminal cells: 20/20; exports completed: 3; failed before export: 17.
- Raw API evidence: 747/747 complete request/response/raw-content sets.
- JSON parse failures preserved: 27; parsed successfully: 720.
- Connection retry warning lines: 13; these are attempt-level warnings.
- Initial raw responses with conservative envelope errors: 19/20.
- Last normalized libraries still containing errors: 18/20.
- Exported final libraries containing errors: 3/3.
- Invalid final libraries accepted by final LLM Review: 2.
- Export byte-consistency passed: 3/3.
- Source/config hashes unchanged: True.

The checks cover conservative outer envelopes and basic lengths. A failure proves a concrete defect; passing does not prove full semantic validity.

## Per-cell matrix

| Project | Mode | Run | Calls | Raw invalid | Last normalized invalid | Final invalid | Seeds | Files | Review false accept |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1.BACnet-stack | base | failed | 37 | 5/5 | 62/93 | 0/0 | 0 | N/A | no |
| 1.BACnet-stack | vk_only | failed | 37 | 1/1 | 1/68 | 0/0 | 0 | N/A | no |
| 1.BACnet-stack | pk_only | completed | 37 | 74/74 | 11/74 | 11/73 | 65 | PASS | no |
| 1.BACnet-stack | full | failed | 37 | 6/6 | 24/55 | 0/0 | 0 | N/A | no |
| 2.libiec61850 | base | failed | 37 | 5/5 | 26/69 | 0/0 | 0 | N/A | no |
| 2.libiec61850 | vk_only | failed | 39 | 4/4 | 8/66 | 0/0 | 0 | N/A | no |
| 2.libiec61850 | pk_only | failed | 37 | 7/7 | 30/57 | 0/0 | 0 | N/A | no |
| 2.libiec61850 | full | failed | 37 | 6/6 | 44/100 | 0/0 | 0 | N/A | no |
| 3.lib60870 | base | failed | 37 | 4/4 | 0/69 | 0/0 | 0 | N/A | no |
| 3.lib60870 | vk_only | failed | 37 | 1/4 | 0/73 | 0/0 | 0 | N/A | no |
| 3.lib60870 | pk_only | failed | 37 | 6/6 | 3/63 | 0/0 | 0 | N/A | no |
| 3.lib60870 | full | failed | 37 | 6/6 | 2/75 | 0/0 | 0 | N/A | no |
| 4.OpENer | base | failed | 37 | 6/6 | 19/85 | 0/0 | 0 | N/A | no |
| 4.OpENer | vk_only | failed | 37 | 1/1 | 21/123 | 0/0 | 0 | N/A | no |
| 4.OpENer | pk_only | failed | 37 | 6/6 | 8/54 | 0/0 | 0 | N/A | no |
| 4.OpENer | full | failed | 41 | 6/6 | 13/79 | 0/0 | 0 | N/A | no |
| 5.libmodbus | base | completed | 38 | 6/6 | 10/113 | 8/109 | 65 | PASS | YES |
| 5.libmodbus | vk_only | failed | 37 | 0/6 | 10/75 | 0/0 | 0 | N/A | no |
| 5.libmodbus | pk_only | completed | 37 | 3/5 | 12/68 | 12/68 | 65 | PASS | YES |
| 5.libmodbus | full | failed | 37 | 5/5 | 14/70 | 0/0 | 0 | N/A | no |

## Interpretation

The dominant export failure is strict equality: only 65 candidates were requested while 65 final sequences were mandatory. Any parse failure, duplicate removal, protocol rejection, or Review rejection makes the target impossible unless revisions restore the full count. All 17 failed cells ended below 65 eligible sequences.

The exported cells were BACnet PK-only, Modbus Base, and Modbus PK-only. Their files are byte-consistent, but all three still contain messages rejected by conservative protocol checks.

## Evidence

- run_config.json: parameters and initial hashes.
- status.json: commands, timing, return codes and paths.
- traces/<mode>/<project>/attempt-001/llm_calls/: raw API evidence.
- traces/<mode>/<project>/attempt-001/stages/: processing snapshots.
- console/<mode>/<project>.log: warnings and errors.
- analysis.json: detailed checks and examples.
- RUN_ANALYSIS.json: integrated result.
- ERROR_PROCESS.md: causal record.

Raw traces contain research inputs and model outputs. Credential values were not recorded, but traces remain sensitive research evidence.
