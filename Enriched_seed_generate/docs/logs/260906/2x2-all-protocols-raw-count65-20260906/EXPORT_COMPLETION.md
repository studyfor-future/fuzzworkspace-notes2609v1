# Export completion report

## Outcome

- Cells with a manifest: 20/20.
- Original complete exports: 3.
- Recovered partial exports: 17.
- Requested seeds: 1300; exported seeds: 1076; shortfall: 224.
- Manifest, sequence-directory, and AFL counts agree for every cell: True.
- Byte consistency checks pass for every cell: True.

## Root cause and repair

The original run raised RuntimeError before finalize_library and export_library whenever the final selector returned fewer than 65 sequences. Recovery replays the same selector against the last normalize-output snapshot and last parsed Review, then exports the available result without padding or duplication.

A first recovery attempt exported 10 cells and failed on 7 because the original exporter embedded long seed IDs and labels in a deep Windows path. The second recovery channel uses short hash-based filesystem names while preserving full IDs and labels inside manifest and sequence JSON. This completed all 17 missing exports.

Recovered outputs are marked partial-selector-eligible. They are not represented as 65 complete or semantically proven seeds.

## Cell index

| Cell | Kind | Source normalized | Exported | Shortfall | Counts | Files |
|---|---|---:|---:|---:|---|---|
| 1.BACnet-stack/base | recovered-partial | 59 | 59 | 6 | PASS | PASS |
| 1.BACnet-stack/vk_only | recovered-partial | 33 | 33 | 32 | PASS | PASS |
| 1.BACnet-stack/pk_only | original-complete | 65 | 65 | 0 | PASS | PASS |
| 1.BACnet-stack/full | recovered-partial | 44 | 44 | 21 | PASS | PASS |
| 2.libiec61850/base | recovered-partial | 54 | 54 | 11 | PASS | PASS |
| 2.libiec61850/vk_only | recovered-partial | 46 | 46 | 19 | PASS | PASS |
| 2.libiec61850/pk_only | recovered-partial | 54 | 54 | 11 | PASS | PASS |
| 2.libiec61850/full | recovered-partial | 53 | 53 | 12 | PASS | PASS |
| 3.lib60870/base | recovered-partial | 57 | 57 | 8 | PASS | PASS |
| 3.lib60870/vk_only | recovered-partial | 53 | 53 | 12 | PASS | PASS |
| 3.lib60870/pk_only | recovered-partial | 49 | 49 | 16 | PASS | PASS |
| 3.lib60870/full | recovered-partial | 56 | 56 | 9 | PASS | PASS |
| 4.OpENer/base | recovered-partial | 59 | 59 | 6 | PASS | PASS |
| 4.OpENer/vk_only | recovered-partial | 51 | 51 | 14 | PASS | PASS |
| 4.OpENer/pk_only | recovered-partial | 47 | 47 | 18 | PASS | PASS |
| 4.OpENer/full | recovered-partial | 47 | 47 | 18 | PASS | PASS |
| 5.libmodbus/base | original-complete | 65 | 65 | 0 | PASS | PASS |
| 5.libmodbus/vk_only | recovered-partial | 58 | 58 | 7 | PASS | PASS |
| 5.libmodbus/pk_only | original-complete | 65 | 65 | 0 | PASS | PASS |
| 5.libmodbus/full | recovered-partial | 61 | 61 | 4 | PASS | PASS |

## Locations

- Original complete exports: D:\mycode\codex\analysis\tools\Enriched_seed_generate\high_quality_seedsv2\diagnostic_count65_20260906
- Recovered partial exports: D:\mycode\codex\analysis\tools\Enriched_seed_generate\high_quality_seedsv2\r65_recovered_partial
- Machine-readable index: export_completion.json
- Recovery details: recovery_export_status.json
- First recovery evidence: recovery_export_status_v1.json and RECOVERY_EXPORT_LOG_v1.md
