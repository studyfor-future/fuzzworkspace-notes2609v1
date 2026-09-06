from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(r"D:\mycode\codex\analysis\tools\Enriched_seed_generate")
TEST_ROOT = PROJECT_ROOT / "docs" / "logs" / "260906" / "2x2-all-protocols-raw-20260906"
TRACE_ROOT = TEST_ROOT / "traces"
OUTPUT_ROOT = PROJECT_ROOT / "high_quality_seedsv2" / "diagnostic_20260906"

PROJECTS = {
    "1.BACnet-stack": ("bacnet", "BACnet"),
    "2.libiec61850": ("iec61850", "IEC61850"),
    "3.lib60870": ("iec60870", "IEC60870"),
    "4.OpENer": ("opener", "OpENer"),
    "5.libmodbus": ("modbus", "Modbus TCP"),
}
MODES = ("base", "vk_only", "pk_only", "full")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_hex(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.replace("\\x", "")
    text = re.sub(r"(?i)\b0x", "", text)
    return re.sub(r"[\s,:;_\-]", "", text).lower()


def message_records(library: Any) -> list[dict[str, Any]]:
    records = []
    if not isinstance(library, dict):
        return records
    for seq_index, sequence in enumerate(library.get("sequences") or []):
        if not isinstance(sequence, dict):
            continue
        seed_id = str(sequence.get("seed_id") or sequence.get("plan_id") or seq_index)
        for msg_index, message in enumerate(sequence.get("messages") or []):
            if not isinstance(message, dict):
                continue
            hx = compact_hex(message.get("hex"))
            records.append({
                "seed_id": seed_id,
                "message_index": msg_index,
                "direction": str(message.get("direction") or ""),
                "label": str(message.get("label") or ""),
                "hex": hx,
            })
    return records


def validate_message(record: dict[str, Any], family: str) -> list[str]:
    hx = record["hex"]
    if not hx:
        return ["missing hex"]
    try:
        raw = bytes.fromhex(hx)
    except ValueError:
        return ["non-hex or odd-length data"]
    n = len(raw)
    reasons: list[str] = []
    direction = record["direction"]

    if family == "modbus":
        if n < 8:
            return [f"Modbus/TCP ADU shorter than 8 bytes ({n})"]
        if raw[2:4] != b"\x00\x00":
            reasons.append("Modbus protocol identifier is not 0x0000")
        declared = int.from_bytes(raw[4:6], "big")
        if declared != n - 6:
            reasons.append(f"MBAP length={declared}, actual unit+PDU={n - 6}")
        fc = raw[7]
        if direction == "client_to_server":
            fixed_min = {
                1: 12, 2: 12, 3: 12, 4: 12, 5: 12, 6: 12,
                8: 12, 15: 13, 16: 13, 22: 14, 23: 17, 24: 10,
            }
            minimum = fixed_min.get(fc, 8)
            if n < minimum:
                reasons.append(f"function 0x{fc:02x} request shorter than {minimum} bytes ({n})")
        elif direction == "server_to_client":
            if fc & 0x80 and n < 9:
                reasons.append("exception response shorter than 9 bytes")
            elif n < 9:
                reasons.append("normal response has no response data")
    elif family == "bacnet":
        if n < 6:
            return [f"BACnet/IP frame shorter than BVLC+NPDU minimum ({n})"]
        if raw[0] != 0x81:
            reasons.append("BACnet/IP BVLC type is not 0x81")
        else:
            declared = int.from_bytes(raw[2:4], "big")
            if declared != n:
                reasons.append(f"BVLC length={declared}, actual={n}")
    elif family == "opener":
        if n < 24:
            return [f"EtherNet/IP encapsulation frame shorter than 24 bytes ({n})"]
        declared = int.from_bytes(raw[2:4], "little")
        if declared != n - 24:
            reasons.append(f"encapsulation payload length={declared}, actual={n - 24}")
    elif family == "iec60870":
        if not raw:
            return ["empty IEC 60870 frame"]
        if raw[0] == 0x68:
            if n >= 4 and raw[3] == 0x68:
                if n < 6:
                    reasons.append(f"FT1.2 variable frame shorter than 6 bytes ({n})")
                elif raw[1] != raw[2]:
                    reasons.append("FT1.2 repeated lengths differ")
            else:
                if n < 6:
                    reasons.append(f"IEC 60870-5-104 APDU shorter than 6 bytes ({n})")
                elif raw[1] != n - 2:
                    reasons.append(f"APCI length={raw[1]}, actual={n - 2}")
        elif raw[0] == 0x10:
            if n < 5 or raw[-1] != 0x16:
                reasons.append("invalid FT1.2 fixed-length envelope")
        else:
            reasons.append("unrecognized IEC 60870 frame start")
    elif family == "iec61850":
        if n < 7:
            return [f"IEC 61850 TPKT/COTP envelope shorter than 7 bytes ({n})"]
        if raw[0] != 0x03 or raw[1] != 0x00:
            reasons.append("TPKT version/reserved bytes are not 03 00")
        declared = int.from_bytes(raw[2:4], "big")
        if declared != n:
            reasons.append(f"TPKT length={declared}, actual={n}")
    return reasons


def assess(records: list[dict[str, Any]], family: str) -> dict[str, Any]:
    invalid = []
    for record in records:
        reasons = validate_message(record, family)
        if reasons:
            invalid.append({
                "seed_id": record["seed_id"],
                "message_index": record["message_index"],
                "direction": record["direction"],
                "label": record["label"],
                "byte_length": len(record["hex"]) // 2,
                "hex_preview": record["hex"][:96],
                "reasons": reasons,
            })
    return {
        "messages": len(records),
        "invalid_messages": len(invalid),
        "valid_messages": len(records) - len(invalid),
        "invalid_examples": invalid[:5],
    }


def load_candidate_calls(trace_dir: Path) -> list[dict[str, Any]]:
    result = []
    calls_dir = trace_dir / "llm_calls"
    if not calls_dir.exists():
        return result
    for call_dir in sorted(p for p in calls_dir.iterdir() if p.is_dir()):
        parsed_path = call_dir / "parsed.json"
        request_path = call_dir / "request.json"
        if not parsed_path.exists() or not request_path.exists():
            continue
        parsed = read_json(parsed_path)
        request = read_json(request_path)
        records = message_records(parsed)
        if records:
            result.append({
                "name": call_dir.name,
                "schema_name": request.get("schema_name"),
                "parsed": parsed,
                "records": records,
            })
    return result


def load_stages(trace_dir: Path, suffix: str) -> list[tuple[str, Any]]:
    stage_dir = trace_dir / "stages"
    if not stage_dir.exists():
        return []
    result = []
    for path in sorted(stage_dir.glob(f"*{suffix}.json")):
        result.append((path.name, read_json(path)))
    return result


def export_check(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return {"exported": False, "file_consistency": None}
    manifest = read_json(manifest_path)
    errors = []
    sequence_dirs = sorted(p for p in (output_dir / "sequences").iterdir() if p.is_dir())
    afl_files = sorted((output_dir / "afl_corpus").glob("*.bin"))
    for index, seq_dir in enumerate(sequence_dirs):
        bin_path = seq_dir / "sequence.bin"
        hex_path = seq_dir / "sequence.hex"
        json_path = seq_dir / "sequence.json"
        if not (bin_path.exists() and hex_path.exists() and json_path.exists()):
            errors.append(f"{seq_dir.name}: missing sequence artifact")
            continue
        raw = bin_path.read_bytes()
        try:
            from_hex = bytes.fromhex(hex_path.read_text(encoding="ascii").strip())
        except Exception as exc:
            errors.append(f"{seq_dir.name}: invalid sequence.hex: {exc}")
            continue
        if raw != from_hex:
            errors.append(f"{seq_dir.name}: sequence.bin differs from sequence.hex")
        read_json(json_path)
        if index >= len(afl_files) or afl_files[index].read_bytes() != raw:
            errors.append(f"{seq_dir.name}: AFL corpus mismatch")
    return {
        "exported": True,
        "manifest_seed_count": len(manifest.get("sequences") or []),
        "sequence_dirs": len(sequence_dirs),
        "afl_files": len(afl_files),
        "file_consistency": not errors,
        "file_errors": errors,
        "manifest": manifest,
    }


def analyze_cell(project: str, family: str, mode: str) -> dict[str, Any]:
    trace_dir = TRACE_ROOT / mode / project
    output_dir = OUTPUT_ROOT / mode / project
    call_dirs = sorted((trace_dir / "llm_calls").glob("*")) if (trace_dir / "llm_calls").exists() else []
    raw_complete = sum(
        all((call / name).exists() for name in ("request.json", "response.json", "raw_content.txt"))
        for call in call_dirs
    )
    candidates = load_candidate_calls(trace_dir)
    initial_raw_records = candidates[0]["records"] if candidates else []

    normalize_inputs = load_stages(trace_dir, "normalize-input")
    normalize_outputs = load_stages(trace_dir, "normalize-output")
    initial_input_library = normalize_inputs[0][1].get("library", {}) if normalize_inputs else {}
    initial_output_payload = normalize_outputs[0][1] if normalize_outputs else {}
    last_output_payload = normalize_outputs[-1][1] if normalize_outputs else {}
    initial_normalized_records = message_records(initial_output_payload.get("library", {}))
    last_normalized_records = message_records(last_output_payload.get("library", {}))

    finals = load_stages(trace_dir, "final-library")
    final_library = finals[-1][1] if finals else {}
    final_records = message_records(final_library)

    raw_assessment = assess(initial_raw_records, family)
    first_norm_assessment = assess(initial_normalized_records, family)
    last_norm_assessment = assess(last_normalized_records, family)
    final_assessment = assess(final_records, family)

    raw_hex = [r["hex"] for r in initial_raw_records]
    input_hex = [r["hex"] for r in message_records(initial_input_library)]
    first_norm_hex = [r["hex"] for r in initial_normalized_records]
    exact_input_match = raw_hex == input_hex
    changed_by_normalization = sum(
        1 for a, b in zip(input_hex, first_norm_hex) if a != b
    ) + abs(len(input_hex) - len(first_norm_hex))

    reviews = []
    for call in sorted(call_dirs):
        parsed_path = call / "parsed.json"
        request_path = call / "request.json"
        if not parsed_path.exists() or not request_path.exists():
            continue
        parsed = read_json(parsed_path)
        request = read_json(request_path)
        if isinstance(parsed, dict) and "needs_revision" in parsed:
            reviews.append({
                "call": call.name,
                "schema_name": request.get("schema_name"),
                "needs_revision": parsed.get("needs_revision"),
                "overall_score": parsed.get("overall_score"),
                "protocol_validity_score": parsed.get("protocol_validity_score"),
                "sequence_feedback": parsed.get("sequence_feedback"),
            })

    export = export_check(output_dir)
    manifest = export.pop("manifest", {}) if export.get("exported") else {}
    final_review = ((manifest.get("run_metadata") or {}).get("final_review") or {}) if manifest else {}
    reviewer_false_accept = bool(
        final_assessment["invalid_messages"]
        and final_review
        and not final_review.get("needs_revision", True)
    )

    if raw_assessment["invalid_messages"]:
        origin = "raw_llm_contains_invalid"
    elif first_norm_assessment["invalid_messages"]:
        origin = "post_processing_introduced_invalid"
    else:
        origin = "no_basic_envelope_error_in_initial_batch"
    if last_norm_assessment["invalid_messages"]:
        validator = "invalid_survived_normalization"
    else:
        validator = "no_basic_envelope_error_after_last_normalization"

    return {
        "project": project,
        "protocol": PROJECTS[project][1],
        "family": family,
        "mode": mode,
        "trace_dir": str(trace_dir),
        "output_dir": str(output_dir),
        "llm_calls": len(call_dirs),
        "complete_raw_responses": raw_complete,
        "candidate_or_revision_calls": len(candidates),
        "initial_raw": raw_assessment,
        "initial_normalized": first_norm_assessment,
        "last_normalized": last_norm_assessment,
        "final": final_assessment,
        "raw_to_normalize_input_exact": exact_input_match,
        "messages_changed_by_normalization": changed_by_normalization,
        "normalize_errors_first": initial_output_payload.get("errors") or [],
        "normalize_errors_last": last_output_payload.get("errors") or [],
        "review_calls": reviews,
        "final_review": {
            "needs_revision": final_review.get("needs_revision"),
            "overall_score": final_review.get("overall_score"),
            "protocol_validity_score": final_review.get("protocol_validity_score"),
        } if final_review else {},
        "reviewer_false_accept": reviewer_false_accept,
        "origin_diagnosis": origin,
        "validator_diagnosis": validator,
        "export": export,
    }


def main() -> None:
    cells = []
    for project, (family, _label) in PROJECTS.items():
        for mode in MODES:
            cells.append(analyze_cell(project, family, mode))

    summary = {
        "cells": len(cells),
        "cells_with_complete_raw_capture": sum(
            c["llm_calls"] == c["complete_raw_responses"] and c["llm_calls"] > 0 for c in cells
        ),
        "total_llm_calls": sum(c["llm_calls"] for c in cells),
        "exported_cells": sum(c["export"]["exported"] for c in cells),
        "failed_to_export_cells": sum(not c["export"]["exported"] for c in cells),
        "file_consistency_pass_cells": sum(c["export"].get("file_consistency") is True for c in cells),
        "initial_raw_invalid_cells": sum(c["initial_raw"]["invalid_messages"] > 0 for c in cells),
        "last_normalized_invalid_cells": sum(c["last_normalized"]["invalid_messages"] > 0 for c in cells),
        "final_invalid_cells": sum(c["final"]["invalid_messages"] > 0 for c in cells),
        "reviewer_false_accept_cells": sum(c["reviewer_false_accept"] for c in cells),
    }
    payload = {"summary": summary, "cells": cells}
    (TEST_ROOT / "analysis.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# All-protocol 2x2 raw LLM diagnostic report - 2026-09-06",
        "",
        "## Scope",
        "",
        "Five protocol projects, four P/V factor cells per project, four requested",
        "candidate seeds and four requested final seeds per cell.",
        "",
        "The validator in this report checks conservative outer-envelope and basic",
        "request-size invariants. It is not a complete semantic protocol decoder.",
        "",
        "## Aggregate result",
        "",
        f"- Test cells: {summary['cells']}",
        f"- Complete raw-response capture: {summary['cells_with_complete_raw_capture']}/{summary['cells']}",
        f"- Total LLM API calls captured: {summary['total_llm_calls']}",
        f"- Cells exported: {summary['exported_cells']}/{summary['cells']}",
        f"- Exported cells with byte-consistent artifacts: {summary['file_consistency_pass_cells']}/{summary['exported_cells']}",
        f"- Initial raw LLM batches containing basic protocol errors: {summary['initial_raw_invalid_cells']}/{summary['cells']}",
        f"- Last normalized batches still containing errors: {summary['last_normalized_invalid_cells']}/{summary['cells']}",
        f"- Exported final libraries containing errors: {summary['final_invalid_cells']}/{summary['cells']}",
        f"- Final LLM reviews that accepted an invalid final library: {summary['reviewer_false_accept_cells']}",
        "",
        "## Matrix",
        "",
        "| Project | Mode | Calls | Raw invalid | Last normalized invalid | Final invalid | Export | Files | Diagnosis |",
        "|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    for c in cells:
        export = "PASS" if c["export"]["exported"] else "NO"
        files = (
            "PASS" if c["export"].get("file_consistency") is True
            else ("N/A" if not c["export"]["exported"] else "FAIL")
        )
        diagnosis = c["origin_diagnosis"] + "; " + c["validator_diagnosis"]
        lines.append(
            f"| {c['project']} | {c['mode']} | {c['llm_calls']} | "
            f"{c['initial_raw']['invalid_messages']}/{c['initial_raw']['messages']} | "
            f"{c['last_normalized']['invalid_messages']}/{c['last_normalized']['messages']} | "
            f"{c['final']['invalid_messages']}/{c['final']['messages']} | "
            f"{export} | {files} | {diagnosis} |"
        )

    lines.extend([
        "",
        "## Error propagation conclusion",
        "",
        "For a cell marked raw_llm_contains_invalid, the first parsed model response",
        "already contains a malformed or incomplete protocol envelope. When the same",
        "cell is marked invalid_survived_normalization, normalize_candidate_library",
        "and repair_protocol_message did not reject or fully repair it. If that cell",
        "also exports invalid final messages, selection and the LLM review allowed the",
        "error into the final corpus.",
        "",
        "The exporter is assessed separately. A file consistency PASS means JSON",
        "parsing succeeded and sequence.hex, sequence.bin, and the AFL corpus bytes",
        "agree. It does not mean the protocol frame itself is valid.",
        "",
        "## Per-cell examples",
        "",
    ])
    for c in cells:
        examples = c["initial_raw"]["invalid_examples"]
        if not examples:
            continue
        lines.append(f"### {c['project']} / {c['mode']}")
        lines.append("")
        for example in examples[:2]:
            reasons = "; ".join(example["reasons"])
            lines.append(
                f"- {example['seed_id']} message {example['message_index']}, "
                f"{example['byte_length']} bytes: {reasons}; "
                f"hex preview: {example['hex_preview']}"
            )
        lines.append("")

    lines.extend([
        "## Evidence locations",
        "",
        "- Raw request/response captures: traces/<mode>/<project>/llm_calls/",
        "- Normalization and final snapshots: traces/<mode>/<project>/stages/",
        "- Machine-readable analysis: analysis.json",
        "- Generated corpora: ../../../../../high_quality_seedsv2/diagnostic_20260906/",
        "",
        "## Source integrity",
        "",
        "Generate copy.py was not modified. The instrumented copy is",
        "Generate diagnostic.py. Its baseline source SHA-256 before and after copying",
        "was F1A8FB2FDA14458BF64A2E35B60AEAF611BA3E107720756BA09D7EF2BE398200.",
        "",
    ])
    (TEST_ROOT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
