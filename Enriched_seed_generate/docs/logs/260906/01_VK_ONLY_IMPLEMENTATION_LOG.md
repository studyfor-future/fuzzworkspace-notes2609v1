# VK-only (P-/V+) Implementation Log

- Date: 2026-09-06
- Modified file: `D:\mycode\codex\analysis\tools\Enriched_seed_generate\Generate copy.py`
- Read-only reference: `D:\mycode\codex\analysis\tools\Enriched_seed_generate\Generate.py`
- Status: implementation and offline regression completed

## Scope and invariants

This change adds VK-only seed generation without structured protocol knowledge.
The existing Full and PK-only path remains the default `legacy` channel.

1. `Generate.py` was read only.
2. The original system prompts and original planning, generation, review, and
   revision prompt source regions were not modified.
3. Copied and adapted VK-only prompts are in a separate template region.
4. Loading, planning, retrieval, generation, review, revision, and selection
   use a separate VK-only path.
5. Protocol-specific repair is disabled by normalizing with
   `protocol_family="generic"`.
6. Generic hex, size, direction, evidence, deduplication, and historical-payload
   collision checks remain active.

## Implementation plan and result

| Step | Planned change | Result |
|---|---|---|
| 1 | Add a VK-only configuration contract | Completed |
| 2 | Load issues without format/function documents | Completed |
| 3 | Add deterministic issue-grounded planning | Completed; 18 plans |
| 4 | Add issue/task-context-only retrieval | Completed |
| 5 | Copy and adapt prompts in a separate region | Completed |
| 6 | Add an independent generator and selector | Completed |
| 7 | Add selectable routing and retain Legacy default | Completed |
| 8 | Run syntax, offline, and CLI tests | Passed |

## New code regions

- `VK_ONLY_SYSTEM_PROMPT` and `VK_ONLY_REVIEW_SYSTEM_PROMPT`
- `VKOnlyConfig`
- `load_vk_only_knowledge` and VK-only context/planning helpers
- four `vk_only_*_prompt` template functions
- `select_vk_only_final_sequences`
- `VKOnlySeedGenerator`
- VK-only CLI parser/config/API helpers
- `run_legacy_channel` and `run_vk_only_channel`

## Channel selection

Legacy remains the default:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --format "<protocol-format-file>" ^
  --functions "<function-code-file>" ^
  --issues "<optional-issue-directory>" ^
  --output "<output-directory>"
```

VK-only must be explicit:

```powershell
conda run -n ICSTsys01-py39 python ".\Generate copy.py" ^
  --generation-channel vk-only ^
  --protocol-name "<protocol-name>" ^
  --issues "<distilled-issue-directory>" ^
  --harness-input "<input-interface-description>" ^
  --sample-shape "message-sequence" ^
  --output-encoding "raw-binary-concat" ^
  --output "<output-directory>"
```

`--protocol-family` is optional metadata and never enables VK-only protocol repair.

## Knowledge boundary

Allowed: protocol name, harness input interface, sample shape, output encoding,
and distilled vulnerability issues.

Excluded: protocol format chunks, operation catalogs, templates, protocol state
machines, undocumented checksum/length/field rules, and protocol-family-specific
repair.

The planner produces exactly `ISSUE_CANDIDATE_COUNT` plans even with one issue.
Every plan carries an issue reference and evidence identifier.

## Verification

All checks used Anaconda environment `ICSTsys01-py39`.

```powershell
conda run -n ICSTsys01-py39 python -m py_compile ".\Generate copy.py"
conda run -n ICSTsys01-py39 python ".\Generate copy.py" --help
conda run -n ICSTsys01-py39 python ".\Generate copy.py" --generation-channel vk-only --help
```

Results:

- syntax compile: passed;
- Legacy prompt source comparison: unchanged;
- default channel routing: Legacy;
- explicit VK-only routing: passed;
- loading without format/functions: passed;
- VK-only format/function chunks: zero;
- deterministic plan count: 18;
- issue/evidence grounding for every plan: passed;
- retrieved kinds limited to issue/task context: passed;
- protocol-specific repair disabled: passed;
- both CLI help smoke tests: passed.

## Integrity evidence

- `Generate.py` SHA-256:
  `3a1e2c945e331fda20c54132f89365d059e11a9fb73014392b8c5494ffdf42cb`
- Modified `Generate copy.py` SHA-256:
  `0be6ae5e219978449aa8345d0e644354a412120b103faa5e77b1faf4511ee4d3`

## Test boundary

No live model/API request was made. A live run still requires model credentials
and real distilled issue documents.
## 2026-09-06 Seed-count scalability update

VK-only counts are now independent from Legacy counts:

- Legacy remains `FINAL_SEED_COUNT = 12` and `ISSUE_CANDIDATE_COUNT = 18`.
- VK-only default final count: `48`.
- VK-only default candidate count: `72`.
- VK-only maximum final count: `100`.
- VK-only maximum candidate count: `150`.

New VK-only options:

```powershell
--final-seed-count 48
--candidate-count 72
```

Recommended presets:

| Profile | Final | Candidate | Intended use |
|---|---:|---:|---|
| Economy | 24 | 36 | quick validation and lower API cost |
| Recommended | 48 | 72 | routine experiments with useful diversity |
| High diversity | 72 | 108 | broader issue/structure coverage |
| Maximum output | 100 | 150 | final large-scale corpus construction |

The candidate count must be greater than or equal to the final count. Boundary
validation runs before model initialization.

VK-only revision was also converted from one large model response to batches of
`CANDIDATE_BATCH_SIZE`. This keeps 72-150 candidate runs within practical
per-response output limits.

Offline regression results:

- default 48/72 parsing: passed;
- explicit 100/150 parsing: passed;
- final-count upper bound: passed;
- selection of 48 results: passed;
- selection of 100 results: passed;
- Legacy 12/18 constants unchanged: passed.

Updated `Generate copy.py` SHA-256:
`89599a96baf0d0e843400740d6ee38c08394a225f9e8ebfbfd7a6ac71e0a3c42`

## Superseding VK-only update  2026-09-06

The earlier `protocol_repair_enabled=False` design in this log is superseded by
`03_CROSS_MODE_100_SEED_SCALING_LOG.md`. VK-only still reads no external
protocol documents, but now permits fallible model internal protocol knowledge,
uses auditable built-in family constraints, and enables family-specific basic
repair for recognized protocols. Final output remains configurable up to 100.

