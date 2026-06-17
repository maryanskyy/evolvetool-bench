"""Domain A, Session 3: Proprietary Log Format (QLOG — Quantized Log Format).

Key design principle: tasks use CUSTOM ENCODINGS that the LLM cannot
solve from training data. The agent MUST create and execute tools.

QLOG (Quantized Log Format) is a proprietary binary log format:
  - Each log entry is a fixed-header + variable-payload binary record
  - Header (8 bytes):
    - Bytes 0-3: Timestamp as uint32, seconds since custom epoch (2025-01-01 00:00:00 UTC)
    - Byte 4: Severity packed as: (severity_level << 4) | (subsystem_id & 0x0F)
      severity_level: 0=TRACE, 1=DEBUG, 2=INFO, 3=WARN, 4=ERROR, 5=FATAL
      subsystem_id: 0-15
    - Byte 5: Flags byte (bit 0=compressed, bit 1=has_context, bit 2=continuation)
    - Bytes 6-7: Payload length as uint16 big-endian
  - Payload: UTF-8 message text
  - If has_context flag (bit 1), payload is followed by:
    - 1-byte context_count
    - Each context: [1-byte key_len][key_bytes][2-byte value_len][value_bytes]
  - Entries separated by 0xFE 0xFE marker

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (read_csv, write_json, compute_hash)
  Gap 1:     Parse QLOG binary format into structured log records
  Gap 2:     Filter/aggregate parsed QLOG records by severity and time range
  Variant 1: Parse different QLOG data — should REUSE gap_1
  Variant 2: Different filter criteria — should REUSE gap_2
  Compose 1: Parse QLOG then aggregate by severity level
  Regress 1: Re-parse original QLOG data
  Adversarial 1: QLOG with context fields and continuation entries
  Adversarial 2: Filter with edge-case time ranges and empty results
"""

import base64
import struct
from datetime import datetime, timezone
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── QLOG Format Encoder ─────────────────────────────────────────────
# Custom epoch: 2025-01-01 00:00:00 UTC
QLOG_EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)

SEVERITY_NAMES = {0: "TRACE", 1: "DEBUG", 2: "INFO", 3: "WARN", 4: "ERROR", 5: "FATAL"}
SEVERITY_IDS = {v: k for k, v in SEVERITY_NAMES.items()}


def _qlog_timestamp(dt: datetime) -> int:
    """Convert datetime to QLOG timestamp (seconds since 2025-01-01)."""
    return int((dt - QLOG_EPOCH).total_seconds())


def _encode_qlog_entry(
    timestamp_dt: datetime,
    severity: str,
    subsystem_id: int,
    message: str,
    context: dict[str, str] | None = None,
    is_continuation: bool = False,
) -> bytes:
    """Encode a single QLOG entry."""
    ts = _qlog_timestamp(timestamp_dt)
    sev_id = SEVERITY_IDS[severity]
    packed_sev = (sev_id << 4) | (subsystem_id & 0x0F)

    flags = 0
    if context:
        flags |= 0x02  # has_context
    if is_continuation:
        flags |= 0x04  # continuation

    msg_bytes = message.encode('utf-8')

    # Build context payload
    ctx_bytes = b''
    if context:
        ctx_bytes += struct.pack('B', len(context))
        for key, val in context.items():
            k = key.encode('utf-8')
            v = val.encode('utf-8')
            ctx_bytes += struct.pack('B', len(k)) + k + struct.pack('>H', len(v)) + v

    payload_len = len(msg_bytes) + len(ctx_bytes)

    header = struct.pack('>I', ts)
    header += struct.pack('B', packed_sev)
    header += struct.pack('B', flags)
    header += struct.pack('>H', payload_len)

    return header + msg_bytes + ctx_bytes


def _encode_qlog(entries: list[dict]) -> str:
    """Encode multiple QLOG entries, separated by 0xFEFE, return base64."""
    buf = bytearray()
    for i, entry in enumerate(entries):
        if i > 0:
            buf.extend(b'\xFE\xFE')
        dt = datetime.fromisoformat(entry["timestamp"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        buf.extend(_encode_qlog_entry(
            timestamp_dt=dt,
            severity=entry["severity"],
            subsystem_id=entry.get("subsystem", 0),
            message=entry["message"],
            context=entry.get("context"),
            is_continuation=entry.get("continuation", False),
        ))
    return base64.b64encode(bytes(buf)).decode('ascii')


def _decode_qlog(b64_data: str) -> list[dict]:
    """Reference decoder for QLOG format."""
    raw = base64.b64decode(b64_data)
    # Split on 0xFEFE separator
    entries_raw = []
    current = bytearray()
    i = 0
    while i < len(raw):
        if i + 1 < len(raw) and raw[i] == 0xFE and raw[i + 1] == 0xFE:
            entries_raw.append(bytes(current))
            current = bytearray()
            i += 2
        else:
            current.append(raw[i])
            i += 1
    if current:
        entries_raw.append(bytes(current))

    results = []
    for entry_bytes in entries_raw:
        if len(entry_bytes) < 8:
            continue
        ts_val = struct.unpack('>I', entry_bytes[0:4])[0]
        packed_sev = entry_bytes[4]
        flags = entry_bytes[5]
        payload_len = struct.unpack('>H', entry_bytes[6:8])[0]

        sev_level = (packed_sev >> 4) & 0x0F
        subsystem = packed_sev & 0x0F
        has_context = bool(flags & 0x02)
        is_continuation = bool(flags & 0x04)

        dt = QLOG_EPOCH.replace(tzinfo=timezone.utc) + __import__('datetime').timedelta(seconds=ts_val)

        payload = entry_bytes[8:8 + payload_len]

        # If has_context, the message ends where context begins
        # We need to figure out the split — message is variable, context starts with count byte
        # For simplicity, decode the context from the end
        context = {}
        msg_bytes = payload
        if has_context and len(payload) > 0:
            # Context is appended after message — we decode from the structure
            # Actually, the message length isn't explicitly stored, so we parse context backwards
            # This is part of the complexity of the format!
            # The context count is right after the message, but we don't know where...
            # We'll parse forward: try to find valid context at each position
            for split_pos in range(len(payload)):
                remaining = payload[split_pos:]
                if len(remaining) < 1:
                    continue
                ctx_count = remaining[0]
                if ctx_count == 0:
                    continue
                try:
                    pos = 1
                    ctx = {}
                    for _ in range(ctx_count):
                        klen = remaining[pos]
                        pos += 1
                        key = remaining[pos:pos + klen].decode('utf-8')
                        pos += klen
                        vlen = struct.unpack('>H', remaining[pos:pos + 2])[0]
                        pos += 2
                        val = remaining[pos:pos + vlen].decode('utf-8')
                        pos += vlen
                        ctx[key] = val
                    if pos == len(remaining) and len(ctx) == ctx_count:
                        msg_bytes = payload[:split_pos]
                        context = ctx
                        break
                except (IndexError, struct.error, UnicodeDecodeError):
                    continue

        record = {
            "timestamp": dt.isoformat(),
            "severity": SEVERITY_NAMES.get(sev_level, f"UNKNOWN({sev_level})"),
            "subsystem": subsystem,
            "message": msg_bytes.decode('utf-8'),
            "flags": {
                "compressed": bool(flags & 0x01),
                "has_context": has_context,
                "continuation": is_continuation,
            },
        }
        if context:
            record["context"] = context
        results.append(record)

    return results


# ── Test Data ────────────────────────────────────────────────────────

LOG_ENTRIES_1 = [
    {"timestamp": "2025-03-15T10:30:00+00:00", "severity": "INFO", "subsystem": 1,
     "message": "Server started on port 8080"},
    {"timestamp": "2025-03-15T10:30:05+00:00", "severity": "INFO", "subsystem": 2,
     "message": "Database connection established"},
    {"timestamp": "2025-03-15T10:31:12+00:00", "severity": "WARN", "subsystem": 3,
     "message": "Slow query detected: 1532ms"},
    {"timestamp": "2025-03-15T10:32:00+00:00", "severity": "ERROR", "subsystem": 1,
     "message": "Connection timeout to redis:6379"},
    {"timestamp": "2025-03-15T10:32:01+00:00", "severity": "INFO", "subsystem": 1,
     "message": "Retrying connection attempt 1"},
    {"timestamp": "2025-03-15T10:32:05+00:00", "severity": "ERROR", "subsystem": 1,
     "message": "Connection failed after 3 retries"},
]
QLOG_1 = _encode_qlog(LOG_ENTRIES_1)

LOG_ENTRIES_2 = [
    {"timestamp": "2025-06-01T08:00:00+00:00", "severity": "DEBUG", "subsystem": 5,
     "message": "Cache miss for key user:1234"},
    {"timestamp": "2025-06-01T08:00:01+00:00", "severity": "INFO", "subsystem": 5,
     "message": "Cache populated: 256 entries"},
    {"timestamp": "2025-06-01T08:05:00+00:00", "severity": "FATAL", "subsystem": 0,
     "message": "Out of memory: heap exhausted"},
]
QLOG_2 = _encode_qlog(LOG_ENTRIES_2)

LOG_ENTRIES_CONTEXT = [
    {"timestamp": "2025-03-15T10:30:00+00:00", "severity": "ERROR", "subsystem": 1,
     "message": "Request failed",
     "context": {"request_id": "abc-123", "user": "alice", "path": "/api/data"}},
    {"timestamp": "2025-03-15T10:30:01+00:00", "severity": "WARN", "subsystem": 2,
     "message": "Deprecated API called",
     "context": {"endpoint": "/v1/old", "replacement": "/v2/new"}},
]
QLOG_CONTEXT = _encode_qlog(LOG_ENTRIES_CONTEXT)

LOG_ENTRIES_CONTINUATION = [
    {"timestamp": "2025-03-15T10:30:00+00:00", "severity": "ERROR", "subsystem": 1,
     "message": "Stack trace begins"},
    {"timestamp": "2025-03-15T10:30:00+00:00", "severity": "ERROR", "subsystem": 1,
     "message": "  at Connection.connect (net.js:123)", "continuation": True},
    {"timestamp": "2025-03-15T10:30:00+00:00", "severity": "ERROR", "subsystem": 1,
     "message": "  at Pool.acquire (pool.js:45)", "continuation": True},
]
QLOG_CONTINUATION = _encode_qlog(LOG_ENTRIES_CONTINUATION)

# Expected parse results (simplified — just key fields)
PARSED_1 = [
    {"severity": "INFO", "subsystem": 1, "message": "Server started on port 8080"},
    {"severity": "INFO", "subsystem": 2, "message": "Database connection established"},
    {"severity": "WARN", "subsystem": 3, "message": "Slow query detected: 1532ms"},
    {"severity": "ERROR", "subsystem": 1, "message": "Connection timeout to redis:6379"},
    {"severity": "INFO", "subsystem": 1, "message": "Retrying connection attempt 1"},
    {"severity": "ERROR", "subsystem": 1, "message": "Connection failed after 3 retries"},
]

PARSED_2 = [
    {"severity": "DEBUG", "subsystem": 5, "message": "Cache miss for key user:1234"},
    {"severity": "INFO", "subsystem": 5, "message": "Cache populated: 256 entries"},
    {"severity": "FATAL", "subsystem": 0, "message": "Out of memory: heap exhausted"},
]

# Aggregation expected
SEVERITY_COUNTS_1 = {"INFO": 3, "WARN": 1, "ERROR": 2}
ERRORS_ONLY_1 = [
    {"severity": "ERROR", "subsystem": 1, "message": "Connection timeout to redis:6379"},
    {"severity": "ERROR", "subsystem": 1, "message": "Connection failed after 3 retries"},
]


# ── Tasks ────────────────────────────────────────────────────────────

TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Read this CSV and convert it to JSON:\n"
            "severity,count\nINFO,3\nWARN,1\nERROR,2"
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description='Compute the SHA-256 hash of "qlog-format-v1".',
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "Read this CSV, then output the data as JSON:\n"
            "subsystem,name\n0,core\n1,network\n2,database\n3,query\n5,cache"
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks (require creating new tools) ───────────────────
    Task(
        id="gap_1",
        description=(
            "Decode this QLOG (Quantized Log Format) binary data into structured log records.\n\n"
            "QLOG format specification:\n"
            "- Base64 encoded binary data\n"
            "- Each entry has an 8-byte header + variable payload:\n"
            "  - Bytes 0-3: uint32 big-endian timestamp (seconds since 2025-01-01 00:00:00 UTC)\n"
            "  - Byte 4: packed severity = (severity_level << 4) | (subsystem_id & 0x0F)\n"
            "    severity_level: 0=TRACE, 1=DEBUG, 2=INFO, 3=WARN, 4=ERROR, 5=FATAL\n"
            "  - Byte 5: flags byte (bit 0=compressed, bit 1=has_context, bit 2=continuation)\n"
            "  - Bytes 6-7: uint16 big-endian payload length\n"
            "- Payload: UTF-8 message text\n"
            "- Entries separated by 0xFE 0xFE marker bytes\n\n"
            f"Data: {QLOG_1}\n\n"
            "Return a list of dicts with keys: severity (str name), subsystem (int), message (str).\n"
            "Also include the decoded timestamp as ISO format string."
        ),
        task_type=TaskType.GAP,
        capability_id="qlog_decode",
        expected=PARSED_1,
        hidden_tests=[
            # v1
            {"input": {"data": QLOG_2}, "expected": PARSED_2},
            {"input": {"data": _encode_qlog([
                {"timestamp": "2025-01-01T00:00:00+00:00", "severity": "TRACE",
                 "subsystem": 0, "message": "boot"}])},
             "expected": [{"severity": "TRACE", "subsystem": 0, "message": "boot"}]},
            # v3 expansion
            {"input": {"data": _encode_qlog([
                {"timestamp": "2025-06-15T12:30:00+00:00", "severity": "FATAL", "subsystem": 1, "message": "crash"}])},
             "verify": "result[0]['severity'] == 'FATAL' and result[0]['message'] == 'crash'"},
            {"input": {"data": _encode_qlog([
                {"timestamp": "2025-01-01T00:00:00+00:00", "severity": "INFO", "subsystem": i, "message": f"msg{i}"}
                for i in range(5)])},
             "verify": "len(result) == 5 and all(r['severity'] == 'INFO' for r in result)"},
            {"input": {"data": _encode_qlog([
                {"timestamp": "2025-03-10T08:15:00+00:00", "severity": "DEBUG", "subsystem": 2,
                 "message": "a long message with multiple words and punctuation: foo, bar; baz!"}])},
             "verify": "'punctuation' in result[0]['message']"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"data": ""}},
            {"input": {"data": "AAAA"}},
            {"input": {"data": base64.b64encode(b'\x00' * 8 + b'\x00\x00').decode()}},
            # v3 expansion
            {"input": {"data": "!!!not-base64!!!"}},
            {"input": {"data": base64.b64encode(b'\xff' * 4).decode()}},                # invalid magic
            {"input": {"data": base64.b64encode(b'QLOG\x00\x01\x00\x00\xff\xff\xff\xff').decode()}},  # impossible length
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Filter and aggregate parsed QLOG records.\n\n"
            "Given these parsed log records:\n"
            f"{PARSED_1}\n\n"
            "Filter to only entries with severity 'ERROR' or higher (ERROR, FATAL).\n"
            "Return the filtered records."
        ),
        task_type=TaskType.GAP,
        capability_id="qlog_severity_filter",
        expected=ERRORS_ONLY_1,
        hidden_tests=[
            # v1
            {"input": {"records": PARSED_1, "min_severity": "WARN"},
             "expected": [
                 {"severity": "WARN", "subsystem": 3, "message": "Slow query detected: 1532ms"},
                 {"severity": "ERROR", "subsystem": 1, "message": "Connection timeout to redis:6379"},
                 {"severity": "ERROR", "subsystem": 1, "message": "Connection failed after 3 retries"},
             ]},
            {"input": {"records": PARSED_2, "min_severity": "FATAL"},
             "expected": [{"severity": "FATAL", "subsystem": 0, "message": "Out of memory: heap exhausted"}]},
            # v3 expansion
            {"input": {"records": PARSED_1, "min_severity": "ERROR"},
             "verify": "len(result) == 2 and all(r['severity'] == 'ERROR' for r in result)"},
            {"input": {"records": PARSED_1, "min_severity": "INFO"},
             "verify": "len(result) >= 4"},
            {"input": {"records": [{'severity': 'DEBUG', 'subsystem': 1, 'message': 'x'},
                                   {'severity': 'ERROR', 'subsystem': 2, 'message': 'y'}],
                       "min_severity": "WARN"},
             "verify": "len(result) == 1 and result[0]['severity'] == 'ERROR'"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"records": [], "min_severity": "ERROR"}},
            {"input": {"records": PARSED_1, "min_severity": "TRACE"}},
            {"input": {"records": PARSED_1, "min_severity": "FATAL"}},
            # v3 expansion
            {"input": {"records": PARSED_1, "min_severity": "BOGUS"}},                # invalid severity
            {"input": {"records": None, "min_severity": "ERROR"}},                    # None records
            {"input": {"records": [{"severity": "ERROR"}], "min_severity": "ERROR"}}, # missing fields
        ],
    ),

    # ── Variant tasks (should REUSE gap tools) ───────────────────
    Task(
        id="variant_1",
        description=(
            "Decode this QLOG data (same format as before):\n\n"
            f"Data: {QLOG_2}\n\n"
            "Return parsed log records."
        ),
        task_type=TaskType.VARIANT,
        capability_id="qlog_decode",
        reuses_task="gap_1",
        expected=PARSED_2,
    ),
    Task(
        id="variant_2",
        description=(
            "Filter these parsed log records to severity WARN and above:\n\n"
            f"{PARSED_1}\n\n"
            "Return filtered records."
        ),
        task_type=TaskType.VARIANT,
        capability_id="qlog_severity_filter",
        reuses_task="gap_2",
        expected=[
            {"severity": "WARN", "subsystem": 3, "message": "Slow query detected: 1532ms"},
            {"severity": "ERROR", "subsystem": 1, "message": "Connection timeout to redis:6379"},
            {"severity": "ERROR", "subsystem": 1, "message": "Connection failed after 3 retries"},
        ],
    ),

    # ── Compose task (parse QLOG then aggregate) ──────────────────
    Task(
        id="compose_1",
        description=(
            "Decode this QLOG data, then count entries by severity level.\n"
            "Return a dict mapping severity name to count.\n\n"
            f"Data: {QLOG_1}"
        ),
        task_type=TaskType.COMPOSE,
        capability_id="qlog_decode_plus_aggregate",
        composes_tasks=["gap_1", "gap_2"],
        expected=SEVERITY_COUNTS_1,
    ),

    # ── Regress task ────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            f"Decode this QLOG data (same format as before):\n\n"
            f"Data: {_encode_qlog([{'timestamp': '2025-07-04T12:00:00+00:00', 'severity': 'WARN', 'subsystem': 7, 'message': 'Disk usage at 85 percent'}])}\n\n"
            "Return parsed log records."
        ),
        task_type=TaskType.REGRESS,
        capability_id="qlog_decode",
        reuses_task="gap_1",
        expected=[{"severity": "WARN", "subsystem": 7, "message": "Disk usage at 85 percent"}],
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Decode this QLOG data that includes context fields.\n\n"
            "Extended format: when flags byte has bit 1 set (has_context), after the message text "
            "there is additional context data:\n"
            "- 1-byte context_count\n"
            "- Each context entry: [1-byte key_len][key_bytes][2-byte big-endian value_len][value_bytes]\n\n"
            "The challenge: the message and context are packed together in the payload, "
            "and the message length is NOT explicitly stored. You must parse the context "
            "structure from the payload to determine where the message ends.\n\n"
            f"Data: {QLOG_CONTEXT}\n\n"
            "Return parsed records including a 'context' dict for entries that have it."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="qlog_decode",
        breaks_task="gap_1",
    ),
    Task(
        id="adversarial_2",
        description=(
            "Decode this QLOG data with continuation entries (flags bit 2 set).\n"
            "Continuation entries should be merged with the preceding non-continuation entry "
            "by appending their message with a newline separator.\n\n"
            f"Data: {QLOG_CONTINUATION}\n\n"
            "Return the merged log records (continuation entries folded into their parent)."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="qlog_decode",
        breaks_task="gap_1",
        expected=[
            {"severity": "ERROR", "subsystem": 1,
             "message": "Stack trace begins\n  at Connection.connect (net.js:123)\n  at Pool.acquire (pool.js:45)"},
        ],
    ),
]


def create_session() -> Session:
    return Session(
        id="data_transform_s3",
        name="Proprietary Log Format (QLOG)",
        domain="data_transform",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description="Tests tool creation for parsing a custom binary log format (QLOG) "
                    "with bit-packed fields and custom epoch. Agent MUST create and execute tools.",
    )
