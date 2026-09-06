from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\mycode\codex\analysis\tools\Enriched_seed_generate")
GENERATOR = ROOT / "Generate diagnostic.py"
ORIGINAL = ROOT / "Generate copy.py"
CONFIG = ROOT / "config.py"
TEST_ROOT = ROOT / "docs" / "logs" / "260906" / "2x2-all-protocols-raw-count65-20260906"
TRACE_ROOT = TEST_ROOT / "traces"
CONSOLE_ROOT = TEST_ROOT / "console"
OUTPUT_ROOT = ROOT / "high_quality_seedsv2" / "diagnostic_count65_20260906"
STATUS_PATH = TEST_ROOT / "status.json"
RUN_CONFIG_PATH = TEST_ROOT / "run_config.json"

FINAL_COUNT = 65
CANDIDATE_COUNT = 65
MAX_WORKERS = 4

EXPECTED_GENERATOR_SHA256 = "9D967E7065AFE04720BDE6DE39256D2E99A9D27CE5933154522851B3D95DA9BC"
EXPECTED_CONFIG_SHA256 = "60B0C244E3B3DB83957789993273F6C5A49AE5AE2672C1035E475C705C477EA7"
EXPECTED_ORIGINAL_SHA256 = "F1A8FB2FDA14458BF64A2E35B60AEAF611BA3E107720756BA09D7EF2BE398200"

PROJECTS = {
    "1.BACnet-stack": {
        "protocol_name": "bacnet-stack",
        "family": "bacnet",
        "format": "protocol_format\\bacnet-stack.json",
        "functions": "function_code\\1.BACnet-stack\\function.txt",
        "issues": "distilled_issue\\1.BACnet-stack",
    },
    "2.libiec61850": {
        "protocol_name": "iec61850",
        "family": "iec61850",
        "format": "protocol_format\\iec61850.json",
        "functions": "function_code\\2.libiec61850\\function.txt",
        "issues": "distilled_issue\\2.libiec61850",
    },
    "3.lib60870": {
        "protocol_name": "iec60870",
        "family": "iec60870",
        "format": "protocol_format\\iec60870.json",
        "functions": "function_code\\3.lib60870\\function.txt",
        "issues": "distilled_issue\\3.lib60870",
    },
    "4.OpENer": {
        "protocol_name": "OpENer",
        "family": "opener",
        "format": "protocol_format\\OpENer.json",
        "functions": "function_code\\4.OpENer\\function.txt",
        "issues": "distilled_issue\\4.OpENer",
    },
    "5.libmodbus": {
        "protocol_name": "modbustcp",
        "family": "modbus",
        "format": "protocol_format\\modbustcp.json",
        "functions": "function_code\\5.libmodbus\\function.txt",
        "issues": "distilled_issue\\5.libmodbus",
    },
}
MODES = ("base", "vk_only", "pk_only", "full")
status_lock = threading.Lock()
status_data: dict[str, object] = {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def set_cell(cell_id: str, **updates: object) -> None:
    with status_lock:
        cells = status_data["cells"]
        assert isinstance(cells, dict)
        cell = cells[cell_id]
        assert isinstance(cell, dict)
        cell.update(updates)
        status_data["updated_at"] = now_iso()
        atomic_json(STATUS_PATH, status_data)


def build_command(project: str, mode: str) -> tuple[list[str], Path, Path]:
    cfg = PROJECTS[project]
    cli_mode = mode.replace("_", "-")
    output_dir = OUTPUT_ROOT / mode / project
    trace_dir = TRACE_ROOT / mode / project / "attempt-001"
    command = [
        sys.executable,
        str(GENERATOR),
        "--generation-channel", cli_mode,
    ]
    if mode == "base":
        command += [
            "--protocol-name", cfg["protocol_name"],
            "--protocol-family", cfg["family"],
        ]
    elif mode == "vk_only":
        command += [
            "--protocol-name", cfg["protocol_name"],
            "--issues", cfg["issues"],
            "--harness-input", "stdin bytes",
            "--sample-shape", "message-sequence",
            "--output-encoding", "raw-binary-concat",
            "--protocol-family", cfg["family"],
        ]
    else:
        command += [
            "--format", cfg["format"],
            "--functions", cfg["functions"],
        ]
        if mode == "full":
            command += ["--issues", cfg["issues"]]
    command += [
        "--final-seed-count", str(FINAL_COUNT),
        "--candidate-count", str(CANDIDATE_COUNT),
        "--output", str(output_dir),
    ]
    return command, trace_dir, output_dir


def run_cell(project: str, mode: str) -> tuple[str, int]:
    cell_id = f"{project}/{mode}"
    command, trace_dir, output_dir = build_command(project, mode)
    console_path = CONSOLE_ROOT / mode / f"{project}.log"
    console_path.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists():
        set_cell(cell_id, state="blocked", error="output directory already exists")
        return cell_id, 2
    if trace_dir.exists():
        set_cell(cell_id, state="blocked", error="trace attempt directory already exists")
        return cell_id, 2

    env = os.environ.copy()
    env["RAW_LLM_TRACE_DIR"] = str(trace_dir)
    started = time.time()
    set_cell(
        cell_id,
        state="running",
        started_at=now_iso(),
        command=command,
        trace_dir=str(trace_dir),
        output_dir=str(output_dir),
        console_log=str(console_path),
    )
    print(f"[START] {cell_id}", flush=True)
    with console_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return_code = process.wait()
    duration = round(time.time() - started, 3)
    manifest = output_dir / "manifest.json"
    call_count = len(list((trace_dir / "llm_calls").glob("*"))) if (trace_dir / "llm_calls").exists() else 0
    final_state = "completed" if return_code == 0 and manifest.exists() else "failed"
    set_cell(
        cell_id,
        state=final_state,
        return_code=return_code,
        finished_at=now_iso(),
        duration_seconds=duration,
        llm_calls=call_count,
        manifest_exists=manifest.exists(),
    )
    print(f"[DONE] {cell_id} state={final_state} code={return_code} calls={call_count}", flush=True)
    return cell_id, return_code


def main() -> int:
    TEST_ROOT.mkdir(parents=True, exist_ok=False)
    observed = {
        "generator_sha256": sha256(GENERATOR),
        "config_sha256": sha256(CONFIG),
        "original_sha256": sha256(ORIGINAL),
    }
    expected = {
        "generator_sha256": EXPECTED_GENERATOR_SHA256,
        "config_sha256": EXPECTED_CONFIG_SHA256,
        "original_sha256": EXPECTED_ORIGINAL_SHA256,
    }
    if observed != expected:
        raise RuntimeError(f"configuration hash mismatch: observed={observed} expected={expected}")

    cells = {}
    for project in PROJECTS:
        for mode in MODES:
            cell_id = f"{project}/{mode}"
            cells[cell_id] = {
                "project": project,
                "mode": mode,
                "state": "pending",
            }

    global status_data
    status_data = {
        "test_id": TEST_ROOT.name,
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "final_seed_count": FINAL_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "max_workers": MAX_WORKERS,
        "cells": cells,
    }
    atomic_json(STATUS_PATH, status_data)
    atomic_json(RUN_CONFIG_PATH, {
        "test_id": TEST_ROOT.name,
        "generator": str(GENERATOR),
        "output_root": str(OUTPUT_ROOT),
        "trace_root": str(TRACE_ROOT),
        "final_seed_count": FINAL_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "maximum_requested_final_seeds": len(PROJECTS) * len(MODES) * FINAL_COUNT,
        "max_workers": MAX_WORKERS,
        "hashes": observed,
        "credential_values_recorded": False,
        "projects": PROJECTS,
        "modes": list(MODES),
    })

    failures = 0
    futures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for project in PROJECTS:
            for mode in MODES:
                futures.append(executor.submit(run_cell, project, mode))
        for future in as_completed(futures):
            _cell_id, return_code = future.result()
            if return_code != 0:
                failures += 1

    final_hashes = {
        "generator_sha256": sha256(GENERATOR),
        "config_sha256": sha256(CONFIG),
        "original_sha256": sha256(ORIGINAL),
    }
    with status_lock:
        status_data["finished_at"] = now_iso()
        status_data["failures"] = failures
        status_data["final_hashes"] = final_hashes
        status_data["hashes_unchanged"] = final_hashes == observed
        atomic_json(STATUS_PATH, status_data)
    print(f"[MATRIX DONE] failures={failures} hashes_unchanged={final_hashes == observed}", flush=True)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
