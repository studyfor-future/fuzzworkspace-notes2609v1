#!/usr/bin/env python3
import argparse
import ast
import json
import os
import re
import struct
import sys
from pathlib import Path


try:
    from config import API_KEY as CONFIG_API_KEY
    from config import BASE_URL as CONFIG_BASE_URL
except (ImportError, AttributeError):
    CONFIG_API_KEY = ""
    CONFIG_BASE_URL = ""


MODEL = "gpt-5.4-xhigh"
API_KEY = str(os.getenv("OPENAI_API_KEY") or CONFIG_API_KEY or "")
BASE_URL = str(os.getenv("OPENAI_BASE_URL") or CONFIG_BASE_URL or "")
REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 24000
API_TIMEOUT_SECONDS = 300.0
API_MAX_RETRIES = 3
MAX_EVIDENCE_ITEMS = 240
MAX_EVIDENCE_TEXT_CHARS = 80000

NOT_PROVIDED = "Not provided in the issue document."
SUMMARY_FALLBACK = "No concise summary could be extracted from the issue document."

FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "Number": {"type": "string"},
        "Summarize": {"type": "string"},
        "Reproduce": {"type": "string"},
    },
    "required": ["Number", "Summarize", "Reproduce"],
    "additionalProperties": False,
}

PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "Payload": {"type": "string"},
        "Reason": {"type": "string"},
    },
    "required": ["Payload", "Reason"],
    "additionalProperties": False,
}

PAYLOAD_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "Accepted": {"type": "boolean"},
        "Payload": {"type": "string"},
        "Reason": {"type": "string"},
    },
    "required": ["Accepted", "Payload", "Reason"],
    "additionalProperties": False,
}

DISTILL_FIELDS_SYSTEM_PROMPT = r"""
You distill security issue documents.

The text inside <source_document> is trusted source material. Use only facts
supported by that source. Do not invent versions, commands, prerequisites,
root causes, impacts, reachability, or remediation details that the document
does not support.

Return the required JSON object.

Field rules:

1. Number
- Copy the supplied document identifier exactly.

2. Summarize
- Give a concise factual account of the affected version when documented, the
  vulnerable component/function/path, the defect or missing validation, the
  triggering condition, and the demonstrated impact.
- Distinguish observed behavior from author speculation.
- Do not infer CVE/CWE/CVSS, RCE, privilege gain, or network reachability
  unless the source explicitly supports it.

3. Reproduce
- Preserve the documented build configuration, target example/program,
  prerequisites, commands, ordered client actions, and the expected crash or
  diagnostic result.
- Condense long PoC source into faithful ordered steps. Do not paste the full
  program here.
- Prefer a useful factual reproduction summary over the generic fallback. Use
  the exact fallback text only when the document truly provides no actionable
  reproduction information at all.
""".strip()

PAYLOAD_EXTRACTION_SYSTEM_PROMPT = r"""
You recover the Payload field from a security issue document.

The text inside <source_document> is trusted source material. Use only bytes or
derivations that are supported by the issue text, the PoC, the mechanically
recognized byte evidence, or the mechanically derived payload candidates.

Return the required JSON object.

Payload rules:

1. Payload means the most complete deterministic attacker-controlled byte
   sequence recoverable from the PoC.
2. Prefer exact client-to-target wire messages in actual send order.
3. If an outer transport or envelope contains runtime-dependent values such as
   server-issued session handles, connection IDs, invoke IDs, sequence numbers,
   or response-derived fields, do not give up immediately. Instead return the
   deepest fully deterministic request bytes that the PoC builds and injects
   toward the vulnerable parser, for example a CIP body, APDU, ASDU, MMS
   request, decoder input buffer, or other inner payload.
4. If the document provides only an exact prefix or preview of the triggering
   bytes, return that exact concrete prefix rather than the generic fallback.
5. Resolve deterministic constructions from the PoC whenever possible:
   bytes.fromhex, byte literals, bytes([...]), bytearray([...]), concatenation,
   repetition, fixed slicing, fixed padding or fill, and struct.pack with fully
   concrete format strings and values.
6. The <hex_evidence> index assigns IDs such as @H0001 to mechanically
   recognized source byte strings. The <payload_candidates> index assigns IDs
   such as @P0001 to mechanically derived payload candidates. When one indexed
   entry exactly matches the correct payload or payload sequence, return that ID
   instead of retranscribing it. For a sequence, return one ID per line in send
   order. The program resolves these IDs before writing the final library.
7. If you do not use an ID, output canonical lowercase hexadecimal bytes only:
   two-digit bytes separated by one ASCII space, one message per line.
8. Do not mix IDs and literal hex lines in one Payload value.
9. Do not output prose, labels, 0x prefixes, \x escapes, angle brackets,
   commas, ellipses, comments, symbolic names, placeholders, or guessed bytes.
10. Never invent hidden runtime values or fill in missing bytes from wishful
    assumptions.
11. Use the exact fallback text only when the document provides no concrete
    attacker-controlled bytes at all.

Reason rules:
- Explain briefly why the selected payload is source-supported.
- If you had to fall back to an inner deterministic payload or exact prefix,
  say that explicitly.
""".strip()

PAYLOAD_AUDIT_SYSTEM_PROMPT = r"""
You independently audit a proposed Payload against an issue document. 

Return the required JSON object:
- Accepted: true only if the returned Payload is fully supported.
- Payload: preferably evidence IDs such as @H0001 or payload-candidate IDs such
  as @P0001, one reference per line in send order; otherwise exact canonical
  hexadecimal bytes; or exactly "Not provided in the issue document." The
  program resolves IDs before writing the final four-field document.
- Reason: a short internal audit explanation.

Audit conservatively:
- Every returned byte must be explicitly present as a client-controlled input
  or be
  mechanically derivable from deterministic source code whose every emitted
  byte is fixed.
- Prefer the most complete deterministic payload. Full wire messages are best,
  but when outer envelopes require runtime-derived values, an exact inner
  request payload is acceptable and should be kept rather than discarded.
- A concrete exact prefix or preview is acceptable when the document only
  exposes that prefix and no fuller deterministic byte sequence exists.
- Reject packet descriptions, server responses, stack/memory hex, guessed
  lengths/checksums, and values obtained from runtime responses.
- Do not fill dynamic session handles, connection IDs, transaction/invoke IDs,
  random values, timestamps, or other placeholders with convenient values.
- Do not omit required earlier messages from a documented multi-message trigger
  merely to make the payload static.
- Do not concatenate independent alternative triggers. Select the first fully
  concrete documented trigger unless the source explicitly requires all
  messages in sequence.
- You may correct formatting or replace the proposal with a better
  source-supported exact sequence. You must not invent.
- Prefer an @Hxxxx or @Pxxxx reference when an indexed entry exactly matches
  the correct sequence. Do not reference a response, address, dump, or
  irrelevant constant.
- Canonical hexadecimal lines contain lowercase two-digit bytes separated by a
  single space and no labels, comments, prefixes, escapes, or placeholders.
""".strip()


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Distill .txt issue documents into a non-overwriting four-field "
            "library with hexadecimal-only wire payloads."
        )
    )
    parser.add_argument(
        "-i",
        required=True,
        metavar="INPUT_DIR",
        help="existing directory containing original .txt issue documents",
    )
    parser.add_argument(
        "-o",
        required=True,
        metavar="OUTPUT_DIR",
        help="append-only distilled library directory; created if absent",
    )
    return parser.parse_args()


def create_client():
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "[WARN] openai package is unavailable; using local fallback distillation.",
            file=sys.stderr,
        )
        return None

    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=API_TIMEOUT_SECONDS,
        max_retries=API_MAX_RETRIES,
    )

    if not hasattr(client, "responses"):
        print(
            "the installed openai package does not provide the Responses API; "
            "using local fallback distillation instead",
            file=sys.stderr,
        )
        return None
    return client


def read_issue(file_path):
    raw = file_path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "utf-16", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def clean_source_for_xml(text):
    # Prevent source text from closing the delimiter used in the prompt.
    return (
        text.replace("</source_document>", "&lt;/source_document&gt;")
        .replace("</hex_evidence>", "&lt;/hex_evidence&gt;")
        .replace("</payload_candidates>", "&lt;/payload_candidates&gt;")
        .replace("</proposed_payload>", "&lt;/proposed_payload&gt;")
    )


def local_document_identifier(text, file_name):
    stem = Path(file_name).stem.strip().lstrip("#").strip()

    if re.fullmatch(r"(?i)CVE-\d{4}-\d+", stem):
        return stem.upper()
    if re.fullmatch(r"(?i)GHSA-[0-9A-Za-z-]+", stem):
        return stem.upper()
    if re.fullmatch(r"\d+", stem):
        return stem

    patterns = (
        r"(?im)^\s*issue\s*#\s*(\d+)\b",
        r"(?im)^\s*#\s*(\d+)\b",
        r"(?i)\b(CVE-\d{4}-\d+)\b",
        r"(?i)\b(GHSA-[0-9A-Za-z-]+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1)
            return value.upper() if not value.isdigit() else value

    return stem or "Unknown"


def _line_number(text, offset):
    return text.count("\n", 0, offset) + 1


def _bytes_to_hex(data):
    return " ".join(f"{byte:02x}" for byte in data)


def canonicalize_hex_line(value):
    """Return canonical hex for one line, or None if it is not pure bytes."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # A continuous hexadecimal stream.
    if re.fullmatch(r"[0-9A-Fa-f]+", text):
        if len(text) % 2:
            return None
        return " ".join(text[i : i + 2].lower() for i in range(0, len(text), 2))

    # Canonical/spaced/comma-separated pairs.
    if re.fullmatch(
        r"[0-9A-Fa-f]{2}(?:[\t ,;:|\-]+[0-9A-Fa-f]{2})*", text
    ):
        tokens = re.findall(r"[0-9A-Fa-f]{2}", text)
        return " ".join(token.lower() for token in tokens)

    # <81><0b> or <0x81> <0x0b>
    if re.fullmatch(r"(?:\s*<(?:0x)?[0-9A-Fa-f]{1,2}>\s*)+", text):
        tokens = re.findall(r"<(?:0x)?([0-9A-Fa-f]{1,2})>", text)
        return " ".join(f"{int(token, 16):02x}" for token in tokens)

    # [81][0b] or [0x81] [0x0b]
    if re.fullmatch(r"(?:\s*\[(?:0x)?[0-9A-Fa-f]{1,2}\]\s*)+", text):
        tokens = re.findall(r"\[(?:0x)?([0-9A-Fa-f]{1,2})\]", text)
        return " ".join(f"{int(token, 16):02x}" for token in tokens)

    # \x81\x0b
    if re.fullmatch(r"(?:\s*\\x[0-9A-Fa-f]{2}\s*)+", text):
        tokens = re.findall(r"\\x([0-9A-Fa-f]{2})", text)
        return " ".join(token.lower() for token in tokens)

    # 0x81, 0x0b
    if re.fullmatch(
        r"(?:\s*0x[0-9A-Fa-f]{1,2}\s*(?:,\s*)?)+", text
    ):
        tokens = re.findall(r"0x([0-9A-Fa-f]{1,2})", text)
        return " ".join(f"{int(token, 16):02x}" for token in tokens)

    return None


def canonicalize_payload(value):
    if isinstance(value, (bytes, bytearray)):
        return _bytes_to_hex(bytes(value))

    if isinstance(value, list):
        raw_lines = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = "" if value is None else str(value).strip()
        if text == NOT_PROVIDED:
            return NOT_PROVIDED
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not raw_lines:
        raise ValueError("Payload is empty")

    canonical_lines = []
    for line in raw_lines:
        canonical = canonicalize_hex_line(line)
        if canonical is None:
            raise ValueError(f"Payload contains non-hexadecimal content: {line[:120]!r}")
        canonical_lines.append(canonical)

    return "\n".join(canonical_lines)


PAYLOAD_REFERENCE_RE = re.compile(r"@(H|P)\d{4}")


def resolve_model_payload(value, evidence, candidates):
    """
    Resolve an internal model Payload into final canonical bytes.

    The model may return evidence IDs or locally derived payload-candidate IDs
    to avoid retranscribing very large source packets. Those IDs are never
    written to the final issue library.
    """
    text = "" if value is None else str(value).strip()
    if text == NOT_PROVIDED:
        return NOT_PROVIDED, "not_provided"

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Payload is empty")

    reference_flags = [bool(PAYLOAD_REFERENCE_RE.fullmatch(line)) for line in lines]
    if any(reference_flags):
        if not all(reference_flags):
            raise ValueError("Payload mixes reference IDs with literal bytes")
        by_id = {item["id"]: item["hex"] for item in evidence}
        by_id.update({item["id"]: item["hex"] for item in candidates})
        resolved = []
        for reference in lines:
            evidence_id = reference[1:]
            if evidence_id not in by_id:
                raise ValueError(f"unknown Payload reference: {reference}")
            resolved.append(by_id[evidence_id])
        return "\n".join(resolved), "reference"

    return canonicalize_payload(text), "literal"


def extract_hex_evidence(text):
    """
    Build a source-side index of common byte representations.

    This index is not treated as authoritative. It is supplied to the model so
    it can distinguish explicit wire bytes from a complete PoC program.
    """
    evidence = []
    seen = set()

    def add(kind, start, raw, canonical):
        if not canonical:
            return
        byte_count = len(canonical.split())
        if byte_count < 2:
            return
        key = (kind, canonical)
        if key in seen:
            return
        seen.add(key)
        line = _line_number(text, start)
        current_line_start = text.rfind("\n", 0, start) + 1
        previous_line_end = max(0, current_line_start - 1)
        previous_line_start = text.rfind("\n", 0, previous_line_end) + 1
        two_lines_back_end = max(0, previous_line_start - 1)
        two_lines_back_start = text.rfind("\n", 0, two_lines_back_end) + 1
        context_start = two_lines_back_start
        context_end = text.find("\n", start + len(raw))
        if context_end < 0:
            context_end = len(text)
        context = text[context_start:context_end].strip()
        evidence.append(
            {
                "kind": kind,
                "line": line,
                "hex": canonical,
                "context": context[:320],
            }
        )

    patterns = (
        (
            "angle-bytes",
            re.compile(r"(?:[ \t]*<(?:0x)?[0-9A-Fa-f]{1,2}>[ \t]*){2,}"),
        ),
        (
            "bracket-bytes",
            re.compile(r"(?:[ \t]*\[(?:0x)?[0-9A-Fa-f]{1,2}\][ \t]*){2,}"),
        ),
        (
            "escaped-bytes",
            re.compile(r"(?:[ \t]*\\x[0-9A-Fa-f]{2}[ \t]*){2,}"),
        ),
        (
            "0x-list",
            re.compile(
                r"(?:0x[0-9A-Fa-f]{1,2}\s*,\s*){2,}"
                r"0x[0-9A-Fa-f]{1,2}"
            ),
        ),
    )

    for kind, pattern in patterns:
        for match in pattern.finditer(text):
            canonical = canonicalize_hex_line(match.group(0))
            add(kind, match.start(), match.group(0), canonical)

    # Single-line spaced streams and continuous streams. Per-line matching
    # avoids accidentally combining unrelated stack-trace lines.
    offset = 0
    for line in text.splitlines(keepends=True):
        line_without_newline = line.rstrip("\r\n")

        for match in re.finditer(
            r"(?<![0-9A-Fa-f])"
            r"(?:[0-9A-Fa-f]{2}[\t ,:|\-]+){3,}"
            r"[0-9A-Fa-f]{2}"
            r"(?![0-9A-Fa-f])",
            line_without_newline,
        ):
            canonical = canonicalize_hex_line(match.group(0))
            add(
                "spaced-stream",
                offset + match.start(),
                match.group(0),
                canonical,
            )

        for match in re.finditer(
            r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8,}(?![0-9A-Fa-f])",
            line_without_newline,
        ):
            canonical = canonicalize_hex_line(match.group(0))
            add(
                "continuous-stream",
                offset + match.start(),
                match.group(0),
                canonical,
            )

        offset += len(line)

    # Simple bytes.fromhex()/bytearray.fromhex() forms, including multiline
    # quoted strings.
    fromhex_pattern = re.compile(
        r"(?is)(?:bytes|bytearray)\.fromhex\(\s*"
        r"(?P<quote>'{3}|\"{3}|'|\")(?P<body>.*?)(?P=quote)\s*\)"
    )
    for match in fromhex_pattern.finditer(text):
        body = match.group("body")
        if re.fullmatch(r"[0-9A-Fa-f\s,:|\-]+", body or ""):
            compact = re.sub(r"[^0-9A-Fa-f]", "", body)
            canonical = canonicalize_hex_line(compact)
            add("fromhex", match.start(), match.group(0), canonical)

    # Simple Python byte literals. ast.literal_eval handles escapes without
    # executing the supplied program.
    bytes_literal_pattern = re.compile(
        r"(?s)(?<![A-Za-z0-9_])(?:br|rb|b)(?P<quote>'{3}|\"{3}|'|\")"
        r"(?P<body>.*?)(?P=quote)",
        re.IGNORECASE,
    )
    for match in bytes_literal_pattern.finditer(text):
        literal = match.group(0)
        try:
            value = ast.literal_eval(literal)
        except (SyntaxError, ValueError):
            continue
        if isinstance(value, bytes) and len(value) >= 2:
            add("python-bytes", match.start(), literal, _bytes_to_hex(value))

    evidence.sort(key=lambda item: (item["line"], item["kind"]))
    evidence = evidence[:MAX_EVIDENCE_ITEMS]
    for index, item in enumerate(evidence, start=1):
        item["id"] = f"H{index:04d}"
    return evidence


def evidence_for_prompt(evidence):
    if not evidence:
        return "No mechanically recognized byte fragments."

    parts = []
    used = 0
    for item in evidence:
        tokens = item["hex"].split()
        if len(tokens) <= 160:
            preview = item["hex"]
        else:
            preview = (
                " ".join(tokens[:96])
                + f" ... [index preview omits {len(tokens) - 128} middle bytes] ... "
                + " ".join(tokens[-32:])
            )
        entry = (
            f'id=@{item["id"]} line={item["line"]} kind={item["kind"]} '
            f'byte_count={len(tokens)}\n'
            f'hex_preview={preview}\n'
            f'context={item["context"]}\n'
        )
        if used + len(entry) > MAX_EVIDENCE_TEXT_CHARS:
            parts.append("[evidence index truncated; the full source document remains above]")
            break
        parts.append(entry)
        used += len(entry)
    return "\n".join(parts)


def _payload_context(text, start, end, limit=320):
    line_start = text.rfind("\n", 0, start) + 1
    prev_start = text.rfind("\n", 0, max(0, line_start - 1)) + 1
    context_end = text.find("\n", end)
    if context_end < 0:
        context_end = len(text)
    return text[prev_start:context_end].strip()[:limit]


def _add_payload_candidate(
    candidates,
    seen,
    kind,
    line,
    context,
    payload,
    *,
    send_index=None,
    completeness="full",
):
    low_context = context.lower()
    if kind == "inline-sequence" and (
        "shadow bytes" in low_context
        or "addresssanitizer" in low_context
        or "read of size" in low_context
        or re.match(r"^\s*0x[0-9a-f]+:", low_context)
    ):
        return

    try:
        canonical = canonicalize_payload(payload)
    except ValueError:
        return

    byte_count = sum(len(item.split()) for item in canonical.splitlines())
    if byte_count < 2:
        return

    key = (kind, canonical, send_index, completeness)
    if key in seen:
        return
    seen.add(key)
    candidates.append(
        {
            "kind": kind,
            "line": line,
            "context": context[:320],
            "hex": canonical,
            "send_index": send_index,
            "completeness": completeness,
        }
    )


def _extract_hex_segments_from_line(line):
    segments = []
    stripped = line.strip()

    if stripped.startswith(("b'", 'b"', "rb'", 'rb"', "br'", 'br"')):
        try:
            value = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            value = None
        if isinstance(value, bytes) and len(value) >= 2:
            segments.append(_bytes_to_hex(value))
            return segments

    candidates = [stripped]
    if ":" in stripped:
        candidates.append(stripped.split(":", 1)[1].strip())
    if re.match(r"^[A-Za-z0-9_.#/-]{1,24}\s+", stripped):
        candidates.append(
            re.sub(r"^[A-Za-z0-9_.#/-]{1,24}\s+", "", stripped, count=1).strip()
        )

    for candidate in candidates:
        canonical = canonicalize_hex_line(candidate)
        if canonical:
            segments.append(canonical)
            continue

        for pattern in (
            r"(?:<(?:0x)?[0-9A-Fa-f]{1,2}>\s*){2,}",
            r"(?:\[(?:0x)?[0-9A-Fa-f]{1,2}\]\s*){2,}",
            r"(?:\\x[0-9A-Fa-f]{2}\s*){2,}",
        ):
            if re.fullmatch(pattern, candidate):
                canonical = canonicalize_hex_line(candidate)
                if canonical:
                    segments.append(canonical)

    return segments


def extract_inline_sequence_candidates(text, candidates, seen):
    trigger_re = re.compile(
        r"(?i)\b(?:poc|proof\s+of\s+concept|payload|send the following|"
        r"sample input|validated|frame|packet|request|trigger)\b"
    )
    lines = text.splitlines()
    armed_until = 0
    current_segments = []
    current_start = 0

    def flush(end_line):
        nonlocal current_segments, current_start
        if not current_segments:
            return
        context = "\n".join(lines[current_start - 1 : end_line])[:320]
        _add_payload_candidate(
            candidates,
            seen,
            "inline-sequence",
            current_start,
            context,
            "\n".join(current_segments),
            completeness="full",
        )
        current_segments = []
        current_start = 0

    for index, line in enumerate(lines, start=1):
        if trigger_re.search(line):
            armed_until = max(armed_until, index + 12)

        segments = _extract_hex_segments_from_line(line)
        if segments and (index <= armed_until or line.strip().startswith("b")):
            if not current_segments:
                current_start = index
            current_segments.extend(segments)
        else:
            flush(index)

    flush(len(lines))


def _strip_c_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//.*", " ", text)
    return text


def _parse_c_byte_expr(expr):
    expr = expr.strip()
    if not expr:
        return None

    char_match = re.fullmatch(r"'(.|\n)'", expr)
    if char_match:
        return ord(char_match.group(1))

    expr = re.sub(r"\(\s*[A-Za-z_][A-Za-z0-9_\s\*]*\)", "", expr)
    probe = re.sub(r"0x[0-9A-Fa-f]+", "", expr)
    if re.search(r"[A-Za-z_]", probe):
        return None
    if not re.fullmatch(r"[0-9xXa-fA-F\s\(\)\|\&\^\+\-\*\/<>]+", expr):
        return None

    try:
        value = eval(expr, {"__builtins__": None}, {})
    except Exception:
        return None
    if not isinstance(value, int):
        return None
    if 0 <= value <= 255:
        return value
    return None


def extract_c_array_candidates(text, candidates, seen):
    init_pattern = re.compile(
        r"(?s)(?:^|[^\w])(?:static\s+)?(?:const\s+)?"
        r"(?:u?int8_t|unsigned\s+char|char)\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\[\s*\d*\s*\]\s*=\s*\{"
        r"(?P<body>.*?)\};"
    )
    for match in init_pattern.finditer(text):
        body = _strip_c_comments(match.group("body"))
        values = []
        for raw in body.split(","):
            item = raw.strip()
            if not item:
                continue
            parsed = _parse_c_byte_expr(item)
            if parsed is None:
                values = []
                break
            values.append(parsed)
        if len(values) >= 2:
            _add_payload_candidate(
                candidates,
                seen,
                "c-array-init",
                _line_number(text, match.start()),
                _payload_context(text, match.start(), match.end()),
                bytes(values),
            )

    assign_pattern = re.compile(
        r"(?m)^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(?P<idx>\d+)\s*\]"
        r"\s*=\s*(?P<expr>[^;]+);"
    )
    by_name = {}
    for match in assign_pattern.finditer(text):
        parsed = _parse_c_byte_expr(_strip_c_comments(match.group("expr")))
        if parsed is None:
            continue
        by_name.setdefault(match.group("name"), []).append(
            (int(match.group("idx")), parsed, match.start(), match.end())
        )

    for name, entries in by_name.items():
        entries.sort()
        indices = [item[0] for item in entries]
        if not indices or indices[0] != 0 or indices != list(range(indices[-1] + 1)):
            continue
        values = [item[1] for item in entries]
        if len(values) < 2:
            continue
        start = entries[0][2]
        end = entries[-1][3]
        _add_payload_candidate(
            candidates,
            seen,
            "c-indexed-buffer",
            _line_number(text, start),
            _payload_context(text, start, end),
            bytes(values),
        )


def _looks_like_python_start(line):
    stripped = line.strip()
    if not stripped:
        return False
    return bool(
        re.match(
            r"(?:#!/.*python|import\b|from\b|def\b|class\b|if\b|with\b|for\b|"
            r"while\b|try:|except\b|return\b|raise\b|[A-Za-z_][A-Za-z0-9_]*\s*=|#)",
            stripped,
        )
    )


def _looks_like_python_continuation(line):
    stripped = line.strip()
    if not stripped:
        return True
    if line.startswith((" ", "\t")):
        return True
    return bool(
        re.search(
            r"(?:\bimport\b|\bfrom\b|\bdef\b|\bclass\b|\bif\b|\bwith\b|\bfor\b|"
            r"\bwhile\b|\btry\b|\bexcept\b|\breturn\b|\braise\b|=|\(|\)|\[|\]|\{|\}|:|"
            r"\.sendall\s*\(|\.sendto\s*\(|\.recv\s*\(|struct\.pack|bytes\.fromhex|"
            r"bytearray|time\.sleep|print\s*\()",
            stripped,
        )
    )


def extract_probable_python_blocks(text):
    blocks = []
    lines = text.splitlines()
    current = []
    start_line = 0
    code_lines = 0

    def flush():
        nonlocal current, start_line, code_lines
        if current and code_lines >= 4:
            blocks.append((start_line, "\n".join(current)))
        current = []
        start_line = 0
        code_lines = 0

    for index, line in enumerate(lines, start=1):
        if not current:
            if _looks_like_python_start(line):
                current = [line]
                start_line = index
                code_lines = 1 if line.strip() else 0
            continue

        if _looks_like_python_continuation(line):
            current.append(line)
            if line.strip():
                code_lines += 1
        else:
            flush()
            if _looks_like_python_start(line):
                current = [line]
                start_line = index
                code_lines = 1 if line.strip() else 0

    flush()
    return blocks


class _ReturnSignal(Exception):
    def __init__(self, value):
        super().__init__("return")
        self.value = value


class SafePythonBytesEvaluator:
    def __init__(self):
        self.env = {}
        self.functions = {}
        self.assignments = []
        self.send_events = []
        self._call_depth = 0

    def eval_expr(self, node, env=None):
        if env is None:
            env = self.env

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise ValueError(f"unknown name: {node.id}")

        if isinstance(node, ast.List):
            return [self.eval_expr(item, env) for item in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.eval_expr(item, env) for item in node.elts)

        if isinstance(node, ast.UnaryOp):
            value = self.eval_expr(node.operand, env)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return +value
            raise ValueError("unsupported unary op")

        if isinstance(node, ast.BinOp):
            left = self.eval_expr(node.left, env)
            right = self.eval_expr(node.right, env)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.BitOr):
                return left | right
            if isinstance(node.op, ast.BitAnd):
                return left & right
            if isinstance(node.op, ast.BitXor):
                return left ^ right
            if isinstance(node.op, ast.LShift):
                return left << right
            if isinstance(node.op, ast.RShift):
                return left >> right
            raise ValueError("unsupported binary op")

        if isinstance(node, ast.Subscript):
            value = self.eval_expr(node.value, env)
            if isinstance(node.slice, ast.Slice):
                lower = self.eval_expr(node.slice.lower, env) if node.slice.lower else None
                upper = self.eval_expr(node.slice.upper, env) if node.slice.upper else None
                step = self.eval_expr(node.slice.step, env) if node.slice.step else None
                return value[slice(lower, upper, step)]
            return value[self.eval_expr(node.slice, env)]

        if isinstance(node, ast.Call):
            return self.eval_call(node, env)

        if isinstance(node, ast.IfExp):
            branch = node.body if self.eval_expr(node.test, env) else node.orelse
            return self.eval_expr(branch, env)

        raise ValueError(f"unsupported expression: {type(node).__name__}")

    def eval_call(self, node, env):
        args = [self.eval_expr(arg, env) for arg in node.args]

        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == "len":
                return len(args[0])
            if name == "bytes":
                if len(args) != 1:
                    raise ValueError("bytes() arity")
                value = args[0]
                if isinstance(value, bytes):
                    return value
                if isinstance(value, bytearray):
                    return bytes(value)
                return bytes(value)
            if name == "bytearray":
                if len(args) != 1:
                    raise ValueError("bytearray() arity")
                return bytes(bytearray(args[0]))
            if name in self.functions:
                return self.call_function(name, args)

        if isinstance(node.func, ast.Attribute):
            owner = node.func.value
            attr = node.func.attr

            if (
                isinstance(owner, ast.Name)
                and owner.id in {"bytes", "bytearray"}
                and attr == "fromhex"
            ):
                return bytes.fromhex(str(args[0]))

            base = self.eval_expr(owner, env)
            if attr == "ljust":
                fill = args[1] if len(args) > 1 else b" "
                return base.ljust(args[0], fill)
            if attr == "encode":
                encoding = args[0] if args else "utf-8"
                return base.encode(encoding)
            if attr == "pack" and base is struct:
                return struct.pack(*args)

        raise ValueError("unsupported call")

    def eval_test(self, node, env):
        if isinstance(node, ast.Compare):
            left = self.eval_expr(node.left, env)
            if len(node.ops) != 1 or len(node.comparators) != 1:
                raise ValueError("complex comparison")
            right = self.eval_expr(node.comparators[0], env)
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.In):
                return left in right
            if isinstance(op, ast.NotIn):
                return left not in right
            if isinstance(op, ast.Lt):
                return left < right
            if isinstance(op, ast.LtE):
                return left <= right
            if isinstance(op, ast.Gt):
                return left > right
            if isinstance(op, ast.GtE):
                return left >= right
        return bool(self.eval_expr(node, env))

    def _record_assignment(self, name, value, line):
        if isinstance(value, (bytes, bytearray)):
            self.assignments.append((name, bytes(value), line))

    def exec_stmt(self, stmt, env=None, line_offset=0):
        if env is None:
            env = self.env

        if isinstance(stmt, ast.FunctionDef):
            self.functions[stmt.name] = stmt
            return

        if isinstance(stmt, ast.Assign):
            value = self.eval_expr(stmt.value, env)
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    env[target.id] = value
                    self._record_assignment(
                        target.id, value, line_offset + getattr(stmt, "lineno", 1) - 1
                    )
            return

        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            current = env.get(stmt.target.id)
            value = self.eval_expr(stmt.value, env)
            if isinstance(stmt.op, ast.Add):
                env[stmt.target.id] = current + value
            else:
                raise ValueError("unsupported augassign")
            self._record_assignment(
                stmt.target.id,
                env[stmt.target.id],
                line_offset + getattr(stmt, "lineno", 1) - 1,
            )
            return

        if isinstance(stmt, ast.With):
            for item in stmt.body:
                try:
                    self.exec_stmt(item, env, line_offset)
                except Exception:
                    continue
            return

        if isinstance(stmt, ast.Try):
            for item in stmt.body:
                try:
                    self.exec_stmt(item, env, line_offset)
                except Exception:
                    continue
            for item in stmt.orelse:
                try:
                    self.exec_stmt(item, env, line_offset)
                except Exception:
                    continue
            for item in stmt.finalbody:
                try:
                    self.exec_stmt(item, env, line_offset)
                except Exception:
                    continue
            return

        if isinstance(stmt, ast.If):
            branch = stmt.body if self.eval_test(stmt.test, env) else stmt.orelse
            for item in branch:
                try:
                    self.exec_stmt(item, env, line_offset)
                except Exception:
                    continue
            return

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute) and call.args:
                attr = call.func.attr
                if attr in {"sendall", "sendto", "send"}:
                    payload = self.eval_expr(call.args[0], env)
                    if isinstance(payload, (bytes, bytearray)):
                        self.send_events.append(
                            (
                                len(self.send_events) + 1,
                                bytes(payload),
                                line_offset + getattr(stmt, "lineno", 1) - 1,
                            )
                        )
            return

        if isinstance(stmt, ast.Return):
            raise _ReturnSignal(self.eval_expr(stmt.value, env))

    def call_function(self, name, args):
        if self._call_depth >= 4:
            raise ValueError("call depth exceeded")
        func = self.functions[name]
        if len(args) != len(func.args.args):
            raise ValueError("unsupported function arity")
        local_env = dict(self.env)
        for param, value in zip(func.args.args, args):
            local_env[param.arg] = value

        self._call_depth += 1
        try:
            for stmt in func.body:
                self.exec_stmt(stmt, local_env, 0)
        except _ReturnSignal as signal:
            return signal.value
        finally:
            self._call_depth -= 1
        raise ValueError("function returned no value")


def infer_python_hints(text):
    hints = {}
    if re.search(r"(?im)^\s*python\d?\s+\S+\s+crash\b", text):
        hints["mode"] = "crash"
    elif re.search(r"(?im)^\s*python\d?\s+\S+\s+baseline\b", text):
        hints["mode"] = "baseline"
    return hints


def extract_python_candidates(text, candidates, seen):
    for start_line, block_text in extract_probable_python_blocks(text):
        try:
            tree = ast.parse(block_text)
        except SyntaxError:
            continue

        evaluator = SafePythonBytesEvaluator()
        for stmt in tree.body:
            try:
                evaluator.exec_stmt(stmt, evaluator.env, start_line)
            except Exception:
                continue

        hints = infer_python_hints(text)
        for func in evaluator.functions.values():
            preview_env = dict(evaluator.env)
            preview_env.update(hints)
            for param in func.args.args:
                preview_env.setdefault(param.arg, None)
            for stmt in func.body:
                try:
                    evaluator.exec_stmt(stmt, preview_env, start_line)
                except Exception:
                    continue

        for name, value, line in evaluator.assignments:
            _add_payload_candidate(
                candidates,
                seen,
                f"python-bytes:{name}",
                line,
                f"Python bytes assignment for {name}",
                value,
            )

        for send_index, payload, line in evaluator.send_events:
            _add_payload_candidate(
                candidates,
                seen,
                "python-send",
                line,
                "Python send/sendall/sendto argument",
                payload,
                send_index=send_index,
            )


def extract_payload_candidates(text):
    candidates = []
    seen = set()
    extract_inline_sequence_candidates(text, candidates, seen)
    extract_c_array_candidates(text, candidates, seen)
    extract_python_candidates(text, candidates, seen)

    candidates.sort(
        key=lambda item: (
            item["send_index"] if item["send_index"] is not None else 1_000_000,
            item["line"],
            item["kind"],
        )
    )
    for index, item in enumerate(candidates, start=1):
        item["id"] = f"P{index:04d}"
    return candidates


def payload_candidates_for_prompt(candidates):
    if not candidates:
        return "No mechanically derived payload candidates."

    parts = []
    for item in candidates:
        entry = (
            f'id=@{item["id"]} line={item["line"]} kind={item["kind"]} '
            f'completeness={item["completeness"]}'
        )
        if item["send_index"] is not None:
            entry += f' send_index={item["send_index"]}'
        entry += (
            f"\nhex_preview={item['hex'][:480]}\n"
            f"context={item['context']}\n"
        )
        parts.append(entry)
    return "\n".join(parts)


def parse_json_object(content):
    content = (content or "").strip()
    if not content:
        raise ValueError("model returned an empty response")

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model response does not contain a JSON object")
        data = json.loads(content[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("model response is not a JSON object")
    return data


def response_output_text(response):
    text = getattr(response, "output_text", None)
    if text:
        return text

    fragments = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                fragments.append(value)
    return "".join(fragments)


def call_structured_json(client, system_prompt, user_prompt, schema_name, schema):
    if client is None:
        raise RuntimeError("model client is unavailable")
    response = client.responses.create(
        model=MODEL,
        reasoning={"effort": REASONING_EFFORT},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        store=False,
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return parse_json_object(response_output_text(response))


def focused_source_text(issue_text):
    if len(issue_text) <= 40000:
        return issue_text

    lines = issue_text.splitlines()
    keep = set()

    def mark_window(center, radius):
        start = max(0, center - radius)
        end = min(len(lines), center + radius + 1)
        keep.update(range(start, end))

    head_chars = 0
    for idx, line in enumerate(lines):
        keep.add(idx)
        head_chars += len(line) + 1
        if head_chars >= 8000:
            break

    tail_chars = 0
    for idx in range(len(lines) - 1, -1, -1):
        keep.add(idx)
        tail_chars += len(lines[idx]) + 1
        if tail_chars >= 2500:
            break

    signal_re = re.compile(
        r"(?i)\b(?:summary|description|details|root cause|poc|proof of concept|"
        r"payload|frame|packet|request|reproduce|steps|asan|ubsan|sendall|sendto|"
        r"bytes\.fromhex|struct\.pack)\b"
    )
    for idx, line in enumerate(lines):
        if signal_re.search(line) or _extract_hex_segments_from_line(line):
            mark_window(idx, 2)

    selected = [lines[idx] for idx in sorted(keep)]
    compact = "\n".join(selected)
    return compact[:45000]


def distill_fields_with_model(client, issue_text, identifier):
    safe_source = clean_source_for_xml(focused_source_text(issue_text))
    user_prompt = f"""
Document identifier: {identifier}

<source_document>
{safe_source}
</source_document>

Distill the source now. Copy the document identifier exactly and obey the
three-field schema.
""".strip()

    return call_structured_json(
        client,
        DISTILL_FIELDS_SYSTEM_PROMPT,
        user_prompt,
        "issue_fields",
        FIELD_SCHEMA,
    )


def extract_payload_with_model(client, issue_text, evidence, candidates):
    safe_source = clean_source_for_xml(focused_source_text(issue_text))
    user_prompt = f"""
<source_document>
{safe_source}
</source_document>

<hex_evidence>
{evidence_for_prompt(evidence)}
</hex_evidence>

<payload_candidates>
{payload_candidates_for_prompt(candidates)}
</payload_candidates>

Recover the Payload now. Favor exact deterministic bytes over the generic
fallback, and use a candidate or evidence ID when one already matches.
""".strip()

    return call_structured_json(
        client,
        PAYLOAD_EXTRACTION_SYSTEM_PROMPT,
        user_prompt,
        "issue_payload",
        PAYLOAD_SCHEMA,
    )


def audit_payload_with_model(client, issue_text, proposed_payload, evidence, candidates):
    safe_source = clean_source_for_xml(focused_source_text(issue_text))
    safe_proposal = str(proposed_payload).replace(
        "</proposed_payload>", "&lt;/proposed_payload&gt;"
    )
    user_prompt = f"""
<source_document>
{safe_source}
</source_document>

<hex_evidence>
{evidence_for_prompt(evidence)}
</hex_evidence>

<payload_candidates>
{payload_candidates_for_prompt(candidates)}
</payload_candidates>

<proposed_payload>
{safe_proposal}
</proposed_payload>

Independently verify the proposed payload. Prefer exact evidence or candidate
references when available. Return a corrected exact sequence only when every
byte and the required send order are supported by the source.
""".strip()

    return call_structured_json(
        client,
        PAYLOAD_AUDIT_SYSTEM_PROMPT,
        user_prompt,
        "payload_audit",
        PAYLOAD_AUDIT_SCHEMA,
    )


def payload_matches_known_source(payload, evidence, candidates):
    if payload == NOT_PROVIDED:
        return False
    known = {item["hex"] for item in evidence}
    known.update({item["hex"] for item in candidates})
    return all(line in known for line in payload.splitlines())


def source_has_payload_material(issue_text, evidence, candidates):
    if evidence or candidates:
        return True
    return bool(
        re.search(
            r"(?i)\b(?:poc|proof\s+of\s+concept|reproducer|trigger|"
            r"sendall|sendto|struct\.pack|bytes\.fromhex|packet)\b",
            issue_text,
        )
    )


def source_uses_dynamic_packet_builder(issue_text):
    return bool(
        re.search(
            r"(?im)(?:struct\.pack|pack_into|socket\.(?:socket|create_connection)|"
            r"\.sendall\s*\(|\.sendto\s*\(|bytearray\s*\(|"
            r"response\.hex\s*\(|unpack_from|recv\s*\(|"
            r"^\s*#include\s*[<\\\"]|^\s*(?:static\s+)?int\s+main\s*\(|"
            r"^\s*def\s+\w+\s*\(|^\s*import\s+socket\b|"
            r"\bsend\s*\(|\bsendto\s*\(|\bconnect\s*\()",
            issue_text,
        )
    )


def text_value(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    value = str(value).strip()
    return value or fallback


def normalize_field_distillation(data, identifier):
    expected = {"Number", "Summarize", "Reproduce"}
    if set(data) != expected:
        missing = sorted(expected - set(data))
        extra = sorted(set(data) - expected)
        raise ValueError(
            f"model returned unexpected field keys; missing={missing}, extra={extra}"
        )

    return {
        "Number": identifier,
        "Summarize": text_value(data.get("Summarize"), SUMMARY_FALLBACK),
        "Reproduce": text_value(data.get("Reproduce"), NOT_PROVIDED),
    }


def _resolved_payload_or_fallback(value, evidence, candidates):
    try:
        return resolve_model_payload(value, evidence, candidates)
    except ValueError:
        return NOT_PROVIDED, "invalid"


def _extract_named_section(issue_text, names):
    pattern = re.compile(
        r"(?ims)^\s*(?:" + "|".join(re.escape(name) for name in names) + r")\s*:?\s*$"
    )
    lines = issue_text.splitlines()
    for index, line in enumerate(lines):
        if pattern.match(line):
            body = []
            for other in lines[index + 1 :]:
                if re.match(r"^\s*[A-Z][A-Za-z0-9 /_-]{1,40}\s*:?\s*$", other):
                    break
                body.append(other)
            text = "\n".join(body).strip()
            if text:
                return text
    return ""


def fallback_fields(issue_text, identifier):
    summary = _extract_named_section(
        issue_text,
        ["Summary", "Description", "Vulnerability Description", "Root cause", "Details"],
    )
    if not summary:
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", issue_text)
            if paragraph.strip()
        ]
        summary = next(
            (
                paragraph
                for paragraph in paragraphs
                if not re.fullmatch(r"(?i)(issue|summary|description|details|poc).*", paragraph)
            ),
            "",
        )
    summary = text_value(summary[:1800], SUMMARY_FALLBACK)

    reproduce = _extract_named_section(
        issue_text,
        [
            "PoC",
            "Proof of Concept",
            "Minimal Python PoC",
            "Single-packet PoC",
            "Validated network PoC stream",
        ],
    )
    command_lines = [
        line.strip()
        for line in issue_text.splitlines()
        if re.search(r"(?i)(?:^python\d?\s|^\./|^\s*cat\s|\bnc\s|\bsendall\b|\bsendto\b)", line)
    ]
    if command_lines:
        extra = "\n".join(command_lines[:8])
        reproduce = f"{reproduce}\n{extra}".strip() if reproduce else extra
    reproduce = text_value(reproduce[:2200], NOT_PROVIDED)

    return {
        "Number": identifier,
        "Summarize": summary,
        "Reproduce": reproduce,
    }


def _candidate_score(item):
    context = item.get("context", "").lower()
    score = sum(len(line.split()) for line in item["hex"].splitlines())
    if item.get("send_index") is not None:
        score += 10_000 - item["send_index"]
    if "send" in item["kind"]:
        score += 250
    if "inline" in item["kind"]:
        score += 180
    if any(
        word in context
        for word in ("poc", "payload", "packet", "frame", "request", "trigger")
    ):
        score += 120
    if any(word in context for word in ("response", "asan", "ubsan", "read of size")):
        score -= 120
    return score


def fallback_payload_from_source(issue_text, evidence, candidates):
    send_candidates = sorted(
        [item for item in candidates if item.get("send_index") is not None],
        key=lambda item: item["send_index"],
    )
    if send_candidates:
        return "\n".join(item["hex"] for item in send_candidates)

    if candidates:
        return max(candidates, key=_candidate_score)["hex"]

    if evidence:
        scored = []
        for item in evidence:
            score = len(item["hex"].split())
            context = item["context"].lower()
            if any(word in context for word in ("poc", "payload", "packet", "frame", "request")):
                score += 120
            if any(word in context for word in ("response", "asan", "ubsan", "read of size")):
                score -= 120
            scored.append((score, item["hex"]))
        if scored:
            return max(scored)[1]

    return NOT_PROVIDED


def finalize_payload(
    client,
    issue_text,
    draft_payload,
    draft_payload_mode,
    raw_proposed_payload,
    evidence,
    candidates,
    fallback_payload,
):
    direct = payload_matches_known_source(draft_payload, evidence, candidates)
    dynamic = source_uses_dynamic_packet_builder(issue_text)
    material = source_has_payload_material(issue_text, evidence, candidates)

    if draft_payload == NOT_PROVIDED and fallback_payload != NOT_PROVIDED:
        draft_payload = fallback_payload
        draft_payload_mode = "fallback"
        raw_proposed_payload = fallback_payload

    needs_audit = (
        client is not None
        and material
        and (
        (draft_payload == NOT_PROVIDED and material)
        or (draft_payload != NOT_PROVIDED and not direct)
        or (draft_payload != NOT_PROVIDED and dynamic)
        or (draft_payload != NOT_PROVIDED and (len(evidence) + len(candidates) > 1))
        or draft_payload_mode == "invalid"
        )
    )
    if not needs_audit:
        return draft_payload, None

    try:
        audit = audit_payload_with_model(
            client, issue_text, raw_proposed_payload, evidence, candidates
        )
    except Exception as exc:
        if draft_payload != NOT_PROVIDED:
            return draft_payload, f"Payload audit fallback after model error: {exc}"
        return fallback_payload, f"Payload fallback after model error: {exc}"

    if set(audit) != {"Accepted", "Payload", "Reason"}:
        raise ValueError("payload auditor returned unexpected keys")

    reason = text_value(audit.get("Reason"), "No audit explanation was returned.")
    try:
        audited_payload, _audited_mode = resolve_model_payload(
            audit.get("Payload"), evidence, candidates
        )
    except ValueError:
        return fallback_payload, (
            "Payload auditor returned non-canonical data; conservative fallback used. "
            + reason
        )

    if not bool(audit.get("Accepted")):
        return fallback_payload, reason

    return audited_payload, reason


def format_issue_output(result):
    number = text_value(result.get("Number"), "Unknown")
    summarize = text_value(result.get("Summarize"), SUMMARY_FALLBACK)
    reproduce = text_value(result.get("Reproduce"), NOT_PROVIDED)
    payload = canonicalize_payload(result.get("Payload"))

    return (
        f"Number: {number}\n\n"
        f"Summarize:\n{summarize}\n\n"
        f"Reproduce:\n{reproduce}\n\n"
        f"Payload:\n{payload}\n"
    )


def write_without_overwrite(output_path, result):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    formatted = format_issue_output(result)
    with output_path.open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(formatted)


def is_within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def distill_issuedoc(input_directory, output_directory):
    input_dir = Path(input_directory).expanduser()
    if not input_dir.exists():
        raise ValueError(f"input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise ValueError(f"input path is not a directory: {input_dir}")

    output_dir = Path(output_directory).expanduser()
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"output path is not a directory: {output_dir}")

    input_resolved = input_dir.resolve()
    output_resolved = output_dir.resolve()
    if input_resolved == output_resolved:
        raise ValueError("input and output directories must be different")
    if is_within(output_resolved, input_resolved) or is_within(
        input_resolved, output_resolved
    ):
        raise ValueError("input and output directories must not be nested")

    output_dir.mkdir(parents=True, exist_ok=True)

    issue_files = sorted(
        (
            file_path
            for file_path in input_dir.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() == ".txt"
        ),
        key=lambda file_path: file_path.relative_to(input_dir).as_posix().casefold(),
    )

    if not issue_files:
        print(f"No .txt issue documents found in: {input_dir}")
        return True

    existing_relative_names = {
        file_path.relative_to(output_dir).as_posix().casefold()
        for file_path in output_dir.rglob("*")
        if file_path.is_file()
    }

    new_files = []
    for file_path in issue_files:
        relative_name = file_path.relative_to(input_dir).as_posix()
        if relative_name.casefold() in existing_relative_names:
            print(f"[SKIP] already in issue library: {relative_name}")
        else:
            new_files.append(file_path)

    if not new_files:
        print("No new issue documents to process.")
        return True

    client = create_client()
    processed = 0
    failed = 0

    for file_path in new_files:
        relative_path = file_path.relative_to(input_dir)
        output_path = output_dir / relative_path

        try:
            issue_text = read_issue(file_path)
            if not issue_text.strip():
                raise ValueError("issue document is empty")

            print(
                f"[PROCESSING] {relative_path.as_posix()} chars={len(issue_text)}",
                flush=True,
            )

            identifier = local_document_identifier(issue_text, file_path.name)
            evidence = extract_hex_evidence(issue_text)
            candidates = extract_payload_candidates(issue_text)
            fallback_result = fallback_fields(issue_text, identifier)

            result = dict(fallback_result)
            if client is not None:
                try:
                    result = normalize_field_distillation(
                        distill_fields_with_model(client, issue_text, identifier),
                        identifier,
                    )
                except Exception as exc:
                    print(
                        f"[FIELDS FALLBACK] {relative_path.as_posix()}: {exc}",
                        flush=True,
                    )

            fallback_payload = fallback_payload_from_source(
                issue_text, evidence, candidates
            )
            raw_payload = fallback_payload
            payload_mode = "fallback"
            if client is not None and source_has_payload_material(
                issue_text, evidence, candidates
            ):
                try:
                    payload_data = extract_payload_with_model(
                        client, issue_text, evidence, candidates
                    )
                    raw_payload = payload_data.get("Payload")
                    resolved_payload, payload_mode = _resolved_payload_or_fallback(
                        raw_payload, evidence, candidates
                    )
                    if resolved_payload != NOT_PROVIDED:
                        fallback_payload = resolved_payload
                except Exception as exc:
                    print(
                        f"[PAYLOAD FALLBACK] {relative_path.as_posix()}: {exc}",
                        flush=True,
                    )

            result["Payload"] = fallback_payload
            final_payload, audit_reason = finalize_payload(
                client,
                issue_text,
                fallback_payload,
                payload_mode,
                raw_payload,
                evidence,
                candidates,
                fallback_payload,
            )
            result["Payload"] = final_payload

            if audit_reason:
                print(f"[PAYLOAD AUDIT] {audit_reason}", flush=True)

            write_without_overwrite(output_path, result)
            existing_relative_names.add(relative_path.as_posix().casefold())
            processed += 1

            print(f"[OK] {relative_path.as_posix()} -> {output_path}")
        except FileExistsError:
            existing_relative_names.add(relative_path.as_posix().casefold())
            print(f"[SKIP] output already exists: {relative_path.as_posix()}")
        except Exception as exc:
            failed += 1
            print(
                f"[ERROR] {relative_path.as_posix()}: {exc}",
                file=sys.stderr,
            )

    skipped = len(issue_files) - len(new_files)
    print(f"Completed: processed={processed}, skipped={skipped}, failed={failed}")
    return failed == 0


def main():
    args = parse_args()
    try:
        return 0 if distill_issuedoc(args.i, args.o) else 1
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
