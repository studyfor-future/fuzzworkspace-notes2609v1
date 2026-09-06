# Error process and attribution - 2026-09-06

## Evidence boundary

All conclusions use the saved API objects, raw model content, parsed JSON,
normalization snapshots, final-library snapshots, and exported files from this
single test run. The protocol checker is conservative and validates outer
envelopes plus selected minimum request sizes; it is not a complete decoder.

## End-to-end error process

1. LLM API response layer
   - 79 API responses were saved completely.
   - 70 responses parsed into the requested JSON shape.
   - 9 responses failed JSON/schema parsing and triggered retry or fallback.
   - Every one of the 20 cells had at least one malformed message in its first
     candidate-bearing raw response. For IEC61850 VK-only, the initial candidate
     attempts failed or produced no usable sequences; the first candidate-bearing
     raw response came from the revision call.

2. Parsed response to normalization input
   - 19 of 20 cells had byte-for-byte identical message hex between the first
     candidate-bearing parsed response and the corresponding normalization input.
   - The IEC61850 VK-only exception is explained by an empty initial normalized
     batch followed by a later revision response.
   - This rules out the JSON parser as the general source of truncation.

3. Deterministic normalization and repair
   - Normalization changed or removed messages in 16 cells.
   - Seven cells still contained malformed envelopes after the last normalization.
   - repair_protocol_message only applies several repairs after a minimum length
     test. A too-short Modbus, OpENer, or other frame can therefore bypass repair.
   - normalize_candidate_library validates hexadecimal syntax, maximum size,
     direction, evidence IDs, duplicates, and historical collisions, but it does
     not enforce protocol minimum frame length or required function fields.

4. Count and selection failures
   - BACnet VK-only: 2 final candidates remained; two duplicates were removed.
   - BACnet Full: 3 remained; one duplicate was removed.
   - IEC61850 Full: 2 remained; two duplicates were removed.
   - OpENer PK-only: 3 remained; one duplicate was removed.
   - These four cells correctly refused export because fewer than four distinct
     sequences remained.

5. LLM review false acceptance
   Six exported cells retained malformed frames while the final review reported
   needs_revision=false and protocol-validity scores from 90 to 98:

   - BACnet PK-only: 10 invalid messages out of 15; score 95.
   - IEC61850 PK-only: 7 invalid messages out of 7; score 95.
   - IEC60870 PK-only: 1 invalid message out of 6; score 98.
   - OpENer Base: 6 invalid messages out of 6; score 90.
   - OpENer VK-only: 8 invalid messages out of 8; score 90.
   - Modbus VK-only: 2 invalid messages out of 6; score 92.

6. Export layer
   - 16 of 20 cells exported a final library.
   - All 16 exported cells passed file-level consistency checks.
   - manifest.json and sequence.json parsed successfully.
   - sequence.hex decoded to sequence.bin exactly.
   - AFL corpus files matched sequence.bin.
   - The exporter preserved the selected bytes and did not cause truncation.

## Attribution

The evidence supports this causal chain:

    malformed or incomplete raw LLM candidate
        -> parser usually preserves the supplied bytes
        -> deterministic repair fixes some length fields but misses short or
           semantically incomplete protocol frames
        -> deterministic normalization allows those frames
        -> LLM review sometimes trusts labels and claimed constraints instead
           of validating the bytes
        -> selection exports malformed protocol messages
        -> binary/hex/JSON exporter writes those selected bytes correctly

The LLM is therefore one source of the protocol errors. The final system failure
is not attributable to the LLM alone: deterministic validation and LLM review
both failed to provide the intended defense-in-depth checks.

## Parse-error distribution

- BACnet Base: 1
- BACnet VK-only: 1
- BACnet Full: 1
- IEC61850 VK-only: 3
- OpENer PK-only: 1
- OpENer Full: 1
- Modbus PK-only: 1

## Evidence files

- REPORT.md: complete matrix and representative raw-message examples.
- analysis.json: machine-readable per-cell counts and diagnoses.
- traces/<mode>/<project>/llm_calls/: request, response, raw content, parsed JSON
  or parse error for every API call.
- traces/<mode>/<project>/stages/: normalization inputs, normalization outputs,
  and final-library snapshots where finalization succeeded.
- Generated corpus root:
  high_quality_seedsv2/diagnostic_20260906/

## Source integrity

The original Generate copy.py was not modified. The instrumented diagnostic
copy is Generate diagnostic.py. The original SHA-256 remained:

    F1A8FB2FDA14458BF64A2E35B60AEAF611BA3E107720756BA09D7EF2BE398200
