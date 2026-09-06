# Base (P-/V-) Implementation Log

- Date: 2026-09-06
- Modified file: `D:\mycode\codex\analysis\tools\Enriched_seed_generate\Generate copy.py`
- Read-only reference: `D:\mycode\codex\analysis\tools\Enriched_seed_generate\Generate.py`
- Channel: `base`
- Status: implementation and offline regression completed

## Experimental definition

Base (P-/V-) reads no external protocol-format document, function/operation
document, or vulnerability issue document. Seed content is generated from the
language model's internal training prior.

For reproducibility and usable output, Base also applies auditable built-in
minimum constraints and the existing deterministic basic protocol repair. Thus
P- means **no externally retrieved protocol knowledge**, not an absence of every
protocol-related prior. This distinction should be reported as a possible
experimental confound.

## Isolation guarantees

1. `Generate.py` remains read only.
2. Original Legacy prompts were not modified.
3. VK-only prompts and call logic were not modified.
4. Base system, planning, generation, review and revision prompts occupy a
   separate template region.
5. Base has an independent config, loader, planner, selector, generator, CLI and
   programmatic API.
6. Base does not instantiate `HybridIndex` and does not call `load_knowledge` or
   `load_vk_only_knowledge`.
7. Base source metadata identifies its sole context as built-in/model-prior
   constraints rather than external evidence.

## Built-in protocol profiles

Minimal profiles are provided for:

- Modbus/TCP;
- BACnet/IP;
- EtherNet/IP/OpenER;
- IEC 60870;
- IEC 61850/MMS;
- generic/unknown protocols.

Each profile contains conservative framing constraints and several message or
operation archetypes. The deterministic planner rotates through archetypes and
seven diversity strategies.

Basic repair uses the existing `repair_protocol_message` implementation:

- Modbus MBAP protocol id, length and selected byte-count fields;
- BACnet BVLC total length;
- EtherNet/IP encapsulation payload length;
- IEC 60870 FT1.2/CS104 length fields;
- IEC 61850 TPKT total length;
- generic protocols receive hex normalization but no family-specific repair.

## Seed counts

| Setting | Default | Maximum |
|---|---:|---:|
| Final seeds | 48 | 100 |
| Candidate seeds | 72 | 150 |

Candidate count must be greater than or equal to final count. Generation and
revision are batched using `CANDIDATE_BATCH_SIZE`.

The Base selector first retains distinct target operations, then distinct
strategies, then fills remaining capacity by score and structural signature.

## CLI

Default recommended run:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --generation-channel base ^
  --protocol-name "libmodbus" ^
  --output "<output-directory>"
```

Maximum-output run:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --generation-channel base ^
  --protocol-name "libmodbus" ^
  --final-seed-count 100 ^
  --candidate-count 150 ^
  --output "<output-directory>"
```

The optional `--protocol-family` selects a profile/repair family when inference
from the protocol name is insufficient.

## Verification

All file operations and tests used `ICSTsys01-py39`.

Offline regression results:

- Python syntax compilation: passed;
- original Legacy prompt source comparison: unchanged;
- Base routing and default 48/72 parsing: passed;
- external format/function/issue chunks: zero;
- 72 deterministic plans: passed;
- Modbus profile archetypes: 12 distinct targets;
- issue references in Base plans: empty;
- built-in constraint source id on every plan: passed;
- Modbus basic repair: passed;
- generic family-specific repair isolation: passed;
- selection of 100 from 150 candidates: passed;
- final-count upper bound 100: passed;
- Base generator contains no external knowledge loader/index call: passed;
- Base CLI help exposes no format/functions/issues arguments: passed.

Integrity evidence:

- `Generate.py` SHA-256:
  `3a1e2c945e331fda20c54132f89365d059e11a9fb73014392b8c5494ffdf42cb`
- Modified `Generate copy.py` SHA-256:
  `0a6af38a93b265390222391855fa83d9ed3d692df461c3b8f57c8855fccc4126`

## Test boundary

No live model/API generation was executed. A live run requires valid model
credentials. Output quality and protocol correctness remain dependent on the
model's internal prior, built-in constraints, and supported repair coverage.

