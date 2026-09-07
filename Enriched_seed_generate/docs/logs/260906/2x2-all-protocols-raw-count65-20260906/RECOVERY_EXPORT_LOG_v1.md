# Partial recovery export log

## Policy

The original generator stopped before export whenever fewer than 65
sequences passed its final selector. This recovery replays the original
selector against the last normalize-output snapshot and last parsed Review,
then exports the available selector-eligible sequences without padding,
duplication, or fabrication.

Selector eligibility is not proof of complete protocol semantic validity.
Every recovered manifest carries this warning and its source evidence paths.

## Result

- Failed source cells considered: 17
- Partial exports completed: 10
- Recovery failures: 7

| Cell | Last normalized | Exported | Shortfall | Files |
|---|---:|---:|---:|---|
| 1.BACnet-stack/base | 59 | 59 | 6 | PASS |
| 1.BACnet-stack/vk_only | 33 | 33 | 32 | PASS |
| 1.BACnet-stack/full | N/A | 0 | 65 | RECOVERY FAILED |
| 2.libiec61850/base | 54 | 54 | 11 | PASS |
| 2.libiec61850/vk_only | N/A | 0 | 65 | RECOVERY FAILED |
| 2.libiec61850/pk_only | 54 | 54 | 11 | PASS |
| 2.libiec61850/full | 53 | 53 | 12 | PASS |
| 3.lib60870/base | 57 | 57 | 8 | PASS |
| 3.lib60870/vk_only | 53 | 53 | 12 | PASS |
| 3.lib60870/pk_only | N/A | 0 | 65 | RECOVERY FAILED |
| 3.lib60870/full | N/A | 0 | 65 | RECOVERY FAILED |
| 4.OpENer/base | 59 | 59 | 6 | PASS |
| 4.OpENer/vk_only | N/A | 0 | 65 | RECOVERY FAILED |
| 4.OpENer/pk_only | 47 | 47 | 18 | PASS |
| 4.OpENer/full | N/A | 0 | 65 | RECOVERY FAILED |
| 5.libmodbus/vk_only | N/A | 0 | 65 | RECOVERY FAILED |
| 5.libmodbus/full | 61 | 61 | 4 | PASS |

## Evidence

- Machine-readable status: recovery_export_status.json
- Recovered outputs: high_quality_seedsv2/diagnostic_count65_20260906_recovered_partial/
- Original raw and stage evidence remains unchanged under traces/.
