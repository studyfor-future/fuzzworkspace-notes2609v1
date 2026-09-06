# Error process record

## Observed causal chain

1. Twenty isolated cells ran with candidate and final counts fixed at 65.
2. All 747/747 LLM call directories retain request.json, response.json and raw_content.txt.
3. Parsing failed for 27 responses; parse_error.txt preserves each failure.
4. Raw parsed LLM output already violated conservative protocol invariants in 19/20 cells, demonstrating an LLM-origin contribution.
5. Invalid messages remained after the last normalization in 18/20 cells, demonstrating incomplete deterministic containment.
6. Seventeen cells fell below 65 eligible sequences after parsing, deduplication, validation, Review and revisions; strict count enforcement stopped export.
7. All 3 exported cells still contained conservative protocol errors.
8. Modbus Base and Modbus PK-only were Review false accepts. BACnet PK-only requested revision, but its allowed cycle still left invalid messages.

## Terminal failure lines

- 1.BACnet-stack/base: Error: only 59 Base final sequences available; required 65
- 1.BACnet-stack/vk_only: Error: only 33 VK-only final sequences available; required 65
- 1.BACnet-stack/full: Error: only 44 scalable Full sequences available; required 65
- 2.libiec61850/base: Error: only 54 Base final sequences available; required 65
- 2.libiec61850/vk_only: Error: only 46 VK-only final sequences available; required 65
- 2.libiec61850/pk_only: Error: only 54 scalable PK-only sequences available; required 65
- 2.libiec61850/full: Error: only 53 scalable Full sequences available; required 65
- 3.lib60870/base: Error: only 57 Base final sequences available; required 65
- 3.lib60870/vk_only: Error: only 53 VK-only final sequences available; required 65
- 3.lib60870/pk_only: Error: only 49 scalable PK-only sequences available; required 65
- 3.lib60870/full: Error: only 56 scalable Full sequences available; required 65
- 4.OpENer/base: Error: only 59 Base final sequences available; required 65
- 4.OpENer/vk_only: Error: only 51 VK-only final sequences available; required 65
- 4.OpENer/pk_only: Error: only 47 scalable PK-only sequences available; required 65
- 4.OpENer/full: Error: only 47 scalable Full sequences available; required 65
- 5.libmodbus/vk_only: Error: only 58 VK-only final sequences available; required 65
- 5.libmodbus/full: Error: only 61 scalable Full sequences available; required 65

## Established findings

- LLM generation contributed errors before normalization.
- Post-processing did not contain every observed error.
- LLM Review missed invalid final data in two cells.
- Export serialization is byte-consistent; it did not create the observed structural defects.

## Limits

- Validators cover outer envelopes and basic length/request-size invariants only.
- Passing means only that these checks found no defect.
- Connection warnings count retries, not missing evidence.

## Source integrity

- generator_sha256: 9D967E7065AFE04720BDE6DE39256D2E99A9D27CE5933154522851B3D95DA9BC
- config_sha256: 60B0C244E3B3DB83957789993273F6C5A49AE5AE2672C1035E475C705C477EA7
- original_sha256: F1A8FB2FDA14458BF64A2E35B60AEAF611BA3E107720756BA09D7EF2BE398200
- All hashes match run_config.json: True.
- Generate diagnostic.py, config.py and Generate copy.py were not modified.
