# Cross-mode 100-seed Scaling Log

- Date: 2026-09-06
- Modified file: `D:\mycode\codex\analysis\tools\Enriched_seed_generate\Generate copy.py`
- Read-only reference: `Generate.py`
- Scope: scalable PK-only, Full and VK-only channels
- Status: implementation and offline regression completed

## Channel model

| Channel | External P | External V | Model internal protocol prior | Built-in constraints/repair |
|---|---:|---:|---:|---:|
| `legacy` | optional by old CLI | optional | original behavior | original behavior |
| `pk-only` | yes | no | allowed for source gaps | enabled |
| `full` | yes | yes | allowed for source gaps | enabled |
| `vk-only` | no | yes | allowed, fallible | enabled for recognized family |
| `base` | no | no | allowed, fallible | enabled for recognized family |

`legacy` retains the original prompts, generator source and 12/14/18 counts.
New scalable modes are explicit parallel choices.

## Counts

| Channel | Final default | Candidate default | Final maximum | Candidate maximum |
|---|---:|---:|---:|---:|
| PK-only | 48 | 72 | 100 | 150 |
| Full | 48 | 90 | 100 | 150 |
| VK-only | 48 | 72 | 100 | 150 |
| Base | 48 | 72 | 100 | 150 |

Generation and revision are batched. Candidate count must be no smaller than
final count.

## Diversity policy

The scalable PK-only/Full/VK-only selectors retain distinct target operations
first, then required strategies, then fill by review score and structural
signature. This favors different operation families, frame structures, message
counts, sizes and state paths over cosmetic byte variants.

For VK-only, deterministic plans now rotate vulnerability issues together with
built-in protocol-family archetypes. For libmodbus this supplies 12 distinct
operation/message archetypes before variants repeat.

## Knowledge and inference rules

PK-only and Full treat supplied protocol sources as authoritative. Model internal
knowledge may conservatively fill documentation gaps but may not contradict
sources and must not be described as externally verified.

VK-only reads no external protocol documents. Its external input is distilled
issue knowledge. It combines issue motifs with model internal protocol prior,
auditable built-in family constraints, and basic deterministic repair.

This means P- denotes **no external protocol retrieval**, not zero protocol
prior. Model training knowledge and built-in repair are potential experimental
confounds and should be disclosed.

## CLI examples

PK-only maximum:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --generation-channel pk-only ^
  --format "<format-file>" ^
  --functions "<function-file>" ^
  --final-seed-count 100 ^
  --candidate-count 150 ^
  --output "<output-directory>"
```

Full maximum:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --generation-channel full ^
  --format "<format-file>" ^
  --functions "<function-file>" ^
  --issues "<issue-directory>" ^
  --final-seed-count 100 ^
  --candidate-count 150 ^
  --output "<output-directory>"
```

VK-only maximum:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --generation-channel vk-only ^
  --protocol-name "libmodbus" ^
  --issues "<issue-directory>" ^
  --harness-input "stdin bytes" ^
  --sample-shape "message-sequence" ^
  --output-encoding "raw-binary-concat" ^
  --final-seed-count 100 ^
  --candidate-count 150 ^
  --output "<output-directory>"
```

## Verification

- syntax compilation: passed;
- original Legacy prompts and `SelfRAGSeedGenerator`: unchanged;
- explicit routing for all five channels: passed;
- PK-only excludes `--issues`: passed;
- Full requires `--issues`: passed;
- PK-only defaults 48/72: passed;
- Full defaults 48/90: passed;
- VK-only defaults 48/72: passed;
- PK-only selection of 100/150: passed;
- Full selection of 100/150: passed;
- VK-only selection of 100/150: passed;
- VK-only model-prior constraints and 12 Modbus archetypes: passed;
- VK-only family-specific basic repair enabled: passed;
- original `Generate.py` SHA-256 unchanged:
  `3a1e2c945e331fda20c54132f89365d059e11a9fb73014392b8c5494ffdf42cb`;
- modified `Generate copy.py` SHA-256:
  `13136439947b6012a2969185bf8d29dd9962d58445df739d18a03a20890a2714`.

No live model/API generation was executed.

