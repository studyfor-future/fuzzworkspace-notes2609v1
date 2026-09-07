from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\mycode\codex\analysis\tools\Enriched_seed_generate")
SOURCE = ROOT / "Generate diagnostic.py"
TEST_ROOT = ROOT / "docs" / "logs" / "260906" / "2x2-all-protocols-raw-count65-20260906"
TRACE_ROOT = TEST_ROOT / "traces"
OUTPUT_ROOT = ROOT / "high_quality_seedsv2" / "diagnostic_count65_20260906_recovered_partial"
REQUESTED_COUNT = 65


def load_module():
    spec = importlib.util.spec_from_file_location("generate_diagnostic_recovery", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.SEQUENCE_ENCODING = "raw-binary-concat"
    return module


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def last_stage(trace_dir: Path, suffix: str) -> tuple[Path, dict[str, Any]]:
    paths = sorted((trace_dir / "stages").glob(f"*{suffix}.json"))
    if not paths:
        raise FileNotFoundError(f"No {suffix} stage in {trace_dir}")
    return paths[-1], read_json(paths[-1])


def last_review(trace_dir: Path) -> tuple[Path, dict[str, Any]]:
    found: list[tuple[Path, dict[str, Any]]] = []
    for call_dir in sorted((trace_dir / "llm_calls").iterdir()):
        parsed = call_dir / "parsed.json"
        if not parsed.exists():
            continue
        value = read_json(parsed)
        if isinstance(value, dict) and "needs_revision" in value and "sequence_feedback" in value:
            found.append((parsed, value))
    if not found:
        raise FileNotFoundError(f"No parsed Review in {trace_dir}")
    return found[-1]


def exported_files_consistent(output_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    manifest = read_json(output_dir / "manifest.json")
    sequences = manifest.get("sequences") or []
    afl_files = sorted((output_dir / "afl_corpus").glob("*.bin"))
    sequence_dirs = sorted(p for p in (output_dir / "sequences").iterdir() if p.is_dir())
    if len(sequences) != len(afl_files) or len(sequences) != len(sequence_dirs):
        errors.append("manifest, sequence directory, and AFL counts differ")
    for index, seq_dir in enumerate(sequence_dirs):
        raw = (seq_dir / "sequence.bin").read_bytes()
        from_hex = bytes.fromhex((seq_dir / "sequence.hex").read_text(encoding="ascii").strip())
        if raw != from_hex:
            errors.append(f"{seq_dir.name}: sequence.bin differs from sequence.hex")
        if index >= len(afl_files) or afl_files[index].read_bytes() != raw:
            errors.append(f"{seq_dir.name}: AFL bytes differ")
    return not errors, errors


def main() -> None:
    if OUTPUT_ROOT.exists():
        raise FileExistsError(f"Recovery output already exists: {OUTPUT_ROOT}")
    status = read_json(TEST_ROOT / "status.json")
    generator = load_module()
    results: list[dict[str, Any]] = []
    OUTPUT_ROOT.mkdir(parents=True)

    for key, cell in status["cells"].items():
        if cell.get("state") != "failed":
            continue
        project = cell["project"]
        mode = cell["mode"]
        trace_dir = TRACE_ROOT / mode / project / "attempt-001"
        output_dir = OUTPUT_ROOT / mode / project
        item: dict[str, Any] = {
            "cell": key,
            "project": project,
            "mode": mode,
            "source_state": cell["state"],
            "requested_final_count": REQUESTED_COUNT,
            "trace_dir": str(trace_dir),
            "output_dir": str(output_dir),
        }
        try:
            stage_path, stage = last_stage(trace_dir, "normalize-output")
            review_path, review = last_review(trace_dir)
            clean = stage["library"]
            review = generator.normalize_review_scores(review)
            if mode == "base":
                selected, selection_report = generator.select_base_final_sequences(
                    clean, review, desired_count=REQUESTED_COUNT
                )
            elif mode == "vk_only":
                selected, selection_report = generator.select_vk_only_final_sequences(
                    clean, review, desired_count=REQUESTED_COUNT
                )
            elif mode in ("pk_only", "full"):
                selected, selection_report = generator.select_protocol_scaled_final_sequences(
                    clean,
                    review,
                    issues_enabled=(mode == "full"),
                    desired_count=REQUESTED_COUNT,
                )
            else:
                raise ValueError(f"Unsupported mode: {mode}")

            recovered = dict(clean)
            recovered["sequences"] = selected
            recovered["run_metadata"] = {
                "generation_channel": mode.replace("_", "-"),
                "recovery_export": True,
                "recovery_policy": "partial-selector-eligible",
                "quality_warning": (
                    "Exported from the original selector result after the strict "
                    "65-count gate failed. Selector eligibility is not proof of "
                    "complete protocol semantic validity."
                ),
                "source_test_id": status["test_id"],
                "source_trace_dir": str(trace_dir),
                "source_normalize_stage": str(stage_path),
                "source_review": str(review_path),
                "requested_final_seed_count": REQUESTED_COUNT,
                "recovered_seed_count": len(selected),
                "shortfall": REQUESTED_COUNT - len(selected),
                "final_review": review,
                "selection_report": selection_report,
                "source_generator_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "recovered_at": datetime.now().astimezone().isoformat(),
            }
            generator.export_library(recovered, output_dir)
            consistent, file_errors = exported_files_consistent(output_dir)
            item.update({
                "state": "exported_partial",
                "last_normalized_count": len(clean.get("sequences") or []),
                "exported_seed_count": len(selected),
                "shortfall": REQUESTED_COUNT - len(selected),
                "manifest": str(output_dir / "manifest.json"),
                "file_consistency": consistent,
                "file_errors": file_errors,
            })
        except Exception as exc:
            item.update({"state": "recovery_failed", "error": f"{type(exc).__name__}: {exc}"})
        results.append(item)

    payload = {
        "source_test_id": status["test_id"],
        "policy": "partial-selector-eligible",
        "requested_count_per_cell": REQUESTED_COUNT,
        "output_root": str(OUTPUT_ROOT),
        "result_count": len(results),
        "exported_partial_cells": sum(r["state"] == "exported_partial" for r in results),
        "recovery_failed_cells": sum(r["state"] == "recovery_failed" for r in results),
        "results": results,
    }
    (TEST_ROOT / "recovery_export_status.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Partial recovery export log",
        "",
        "## Policy",
        "",
        "The original generator stopped before export whenever fewer than 65",
        "sequences passed its final selector. This recovery replays the original",
        "selector against the last normalize-output snapshot and last parsed Review,",
        "then exports the available selector-eligible sequences without padding,",
        "duplication, or fabrication.",
        "",
        "Selector eligibility is not proof of complete protocol semantic validity.",
        "Every recovered manifest carries this warning and its source evidence paths.",
        "",
        "## Result",
        "",
        f"- Failed source cells considered: {len(results)}",
        f"- Partial exports completed: {payload['exported_partial_cells']}",
        f"- Recovery failures: {payload['recovery_failed_cells']}",
        "",
        "| Cell | Last normalized | Exported | Shortfall | Files |",
        "|---|---:|---:|---:|---|",
    ]
    for result in results:
        if result["state"] == "exported_partial":
            lines.append(
                f"| {result['cell']} | {result['last_normalized_count']} | "
                f"{result['exported_seed_count']} | {result['shortfall']} | "
                f"{'PASS' if result['file_consistency'] else 'FAIL'} |"
            )
        else:
            lines.append(f"| {result['cell']} | N/A | 0 | 65 | RECOVERY FAILED |")
    lines.extend([
        "",
        "## Evidence",
        "",
        "- Machine-readable status: recovery_export_status.json",
        "- Recovered outputs: high_quality_seedsv2/diagnostic_count65_20260906_recovered_partial/",
        "- Original raw and stage evidence remains unchanged under traces/.",
        "",
    ])
    (TEST_ROOT / "RECOVERY_EXPORT_LOG.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(json.dumps({
        "exported_partial_cells": payload["exported_partial_cells"],
        "recovery_failed_cells": payload["recovery_failed_cells"],
        "output_root": str(OUTPUT_ROOT),
    }, indent=2))


if __name__ == "__main__":
    main()
