"""Domain A, Session 1: Proprietary format processing.

Key design principle: tasks use CUSTOM ENCODINGS that the LLM cannot
solve from training data. The agent MUST create and execute tools.

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (read_csv, write_json, compute_hash)
  Gap 1:     Decode ARISE Binary Record format (custom encoding)
  Gap 2:     Parse run-length encoded matrix
  Variant 1: Decode ARISE Binary Records with different field spec
  Variant 2: Parse RLE matrix with different dimensions
  Compose 1: Decode binary records → hash each record → output JSON
  Regress 1: Re-decode the original binary records
  Adversarial 1: Binary records with escaped delimiters
  Adversarial 2: RLE matrix with zero-runs and negative values
"""

import base64
import json
import struct
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── Custom format: ARISE Binary Records ──────────────────────────────
# Format: each record is [1-byte field_count][fields...]
# Each field: [1-byte name_len][name_bytes][2-byte big-endian value_len][value_bytes]
# Records separated by 0xFF byte

def _encode_abr(records: list[dict[str, str]]) -> str:
    """Encode records into ARISE Binary Record format, return base64."""
    buf = bytearray()
    for i, rec in enumerate(records):
        if i > 0:
            buf.append(0xFF)  # record separator
        buf.append(len(rec))  # field count
        for name, value in rec.items():
            name_bytes = name.encode('utf-8')
            value_bytes = value.encode('utf-8')
            buf.append(len(name_bytes))
            buf.extend(name_bytes)
            buf.extend(struct.pack('>H', len(value_bytes)))
            buf.extend(value_bytes)
    return base64.b64encode(bytes(buf)).decode('ascii')


def _encode_rle_matrix(matrix: list[list[int]]) -> str:
    """Run-length encode a matrix. Format: rows,cols;val:count,val:count,..."""
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    flat = [v for row in matrix for v in row]
    runs = []
    i = 0
    while i < len(flat):
        val = flat[i]
        count = 1
        while i + count < len(flat) and flat[i + count] == val:
            count += 1
        runs.append(f"{val}:{count}")
        i += count
    return f"{rows},{cols};" + ",".join(runs)


# Test data
RECORDS_1 = [
    {"name": "Alice", "role": "engineer", "id": "1001"},
    {"name": "Bob", "role": "designer", "id": "1002"},
    {"name": "Charlie", "role": "manager", "id": "1003"},
]
ABR_1 = _encode_abr(RECORDS_1)

RECORDS_2 = [
    {"city": "NYC", "temp": "72", "humidity": "45"},
    {"city": "LA", "temp": "85", "humidity": "30"},
]
ABR_2 = _encode_abr(RECORDS_2)

RECORDS_ESCAPED = [
    {"name": "Alice\xff", "note": "test"},  # This will need escaping
]
# For adversarial, create records where values contain 0xFF bytes
ABR_ESCAPED = base64.b64encode(
    b'\x02'                                    # 2 fields
    b'\x04name\x00\x0bHello\xfeWorld'          # name = "Hello\xfeWorld" (almost 0xFF)
    b'\x04note\x00\x04test'                     # note = "test"
    b'\xff'                                     # separator
    b'\x01'                                     # 1 field
    b'\x02id\x00\x031\x002'                     # id with null byte in value
).decode('ascii')

MATRIX_1 = [
    [1, 1, 1, 0, 0],
    [0, 0, 2, 2, 2],
    [3, 3, 3, 3, 3],
]
RLE_1 = _encode_rle_matrix(MATRIX_1)

MATRIX_2 = [
    [5, 5, 0, 0, 0, 0],
    [0, 0, 0, 5, 5, 5],
]
RLE_2 = _encode_rle_matrix(MATRIX_2)

MATRIX_ADVERSARIAL = [
    [0, 0, 0, 0],
    [-1, -1, 0, 0],
    [999, 0, 0, 0],
]
RLE_ADVERSARIAL = _encode_rle_matrix(MATRIX_ADVERSARIAL)


TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Read this CSV and convert it to JSON:\n"
            "name,age,city\nAlice,30,NYC\nBob,25,SF\nCharlie,35,LA\nDiana,28,Boston\nEve,32,Seattle"
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description='Compute the SHA-256 hash of "evolvetool-bench-2026".',
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "Read this CSV, then output the data as JSON:\n"
            "product,price,qty\nWidget,9.99,100\nGadget,24.99,50\nDoohickey,4.99,200"
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks (require creating new tools) ───────────────────
    Task(
        id="gap_1",
        description=(
            "Decode this ARISE Binary Record (ABR) format data. The format is:\n"
            "- Base64 encoded binary\n"
            "- Each record: [1-byte field_count][fields...]\n"
            "- Each field: [1-byte name_len][name_bytes][2-byte big-endian value_len][value_bytes]\n"
            "- Records separated by 0xFF byte\n\n"
            f"Data: {ABR_1}\n\n"
            "Return the decoded records as a JSON array of objects."
        ),
        task_type=TaskType.GAP,
        capability_id="abr_binary_decode",
        expected=RECORDS_1,
        hidden_tests=[
            # v1 cases
            {"input": {"data": ABR_2}, "expected": RECORDS_2},
            {"input": {"data": _encode_abr([{"x": "1"}])}, "expected": [{"x": "1"}]},
            # v3 expansion: more diverse inputs to tighten statistical power on C
            {"input": {"data": _encode_abr([{"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}])},
             "expected": [{"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}]},
            {"input": {"data": _encode_abr([{"k": "v1"}, {"k": "v2"}, {"k": "v3"}])},
             "expected": [{"k": "v1"}, {"k": "v2"}, {"k": "v3"}]},
            {"input": {"data": _encode_abr([{"big": "x" * 300}])},
             "expected": [{"big": "x" * 300}]},
            {"input": {"data": _encode_abr([{"unicode": "café 🎯 αβγ"}])},
             "expected": [{"unicode": "café 🎯 αβγ"}]},
        ],
        adversarial_tests=[
            # v1 cases
            {"input": {"data": ""}},
            {"input": {"data": "AAAA"}},
            {"input": {"data": base64.b64encode(b'\x00').decode()}},
            # v3 expansion
            {"input": {"data": "!!!not-base64!!!"}},
            {"input": {"data": base64.b64encode(b'\xff' * 200).decode()}},
            {"input": {"data": base64.b64encode(b'\x02\x04name').decode()}},  # truncated mid-record
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Parse this Run-Length Encoded (RLE) matrix format and reconstruct the matrix.\n"
            "Format: 'rows,cols;val:count,val:count,...'\n"
            "Each 'val:count' means the value 'val' appears 'count' consecutive times.\n\n"
            f"Data: {RLE_1}\n\n"
            "Return the matrix as a list of lists (rows x cols)."
        ),
        task_type=TaskType.GAP,
        capability_id="rle_decompress",
        expected=MATRIX_1,
        hidden_tests=[
            # v1 cases
            {"input": {"rle_string": _encode_rle_matrix([[7, 7], [7, 7]])},
             "expected": [[7, 7], [7, 7]]},
            {"input": {"rle_string": "1,5;1:1,2:1,3:1,4:1,5:1"},
             "expected": [[1, 2, 3, 4, 5]]},
            # v3 expansion
            {"input": {"rle_string": _encode_rle_matrix([[1, 2, 3, 4], [4, 3, 2, 1], [1, 1, 1, 1], [0, 0, 0, 0]])},
             "expected": [[1, 2, 3, 4], [4, 3, 2, 1], [1, 1, 1, 1], [0, 0, 0, 0]]},
            {"input": {"rle_string": "1,20;9:20"}, "expected": [[9] * 20]},
            {"input": {"rle_string": _encode_rle_matrix([[i % 3 for i in range(12)]])},
             "expected": [[i % 3 for i in range(12)]]},
            {"input": {"rle_string": _encode_rle_matrix([[100, 100, 100], [200, 200, 200]])},
             "expected": [[100, 100, 100], [200, 200, 200]]},
        ],
        adversarial_tests=[
            # v1 cases
            {"input": {"rle_string": "0,0;"}},
            {"input": {"rle_string": "1,1;0:1"}},
            {"input": {"rle_string": "2,3;-1:3,0:3"}},
            # v3 expansion
            {"input": {"rle_string": "malformed input"}},                 # no semicolon
            {"input": {"rle_string": "3,3;1:5"}},                          # count mismatches dims
            {"input": {"rle_string": "5,5;val:notanumber"}},               # non-integer count
        ],
    ),

    # ── Variant tasks (should REUSE gap tools) ───────────────────
    Task(
        id="variant_1",
        description=(
            "Decode this ABR (ARISE Binary Record) format data. Same format as before.\n\n"
            f"Data: {ABR_2}\n\n"
            "Return as JSON array of objects."
        ),
        task_type=TaskType.VARIANT,
        capability_id="abr_binary_decode",
        reuses_task="gap_1",
        expected=RECORDS_2,
    ),
    Task(
        id="variant_2",
        description=(
            "Parse this RLE matrix. Same format as before.\n\n"
            f"Data: {RLE_2}\n\n"
            "Return as list of lists."
        ),
        task_type=TaskType.VARIANT,
        capability_id="rle_decompress",
        reuses_task="gap_2",
        expected=MATRIX_2,
    ),

    # ── Compose task (chain gap_1 + seed hash tool) ──────────────
    Task(
        id="compose_1",
        description=(
            "Decode this ABR data, then compute the SHA-256 hash of each record's 'name' field, "
            "and return a JSON array of objects with 'name' and 'name_hash' fields.\n\n"
            f"Data: {ABR_1}"
        ),
        task_type=TaskType.COMPOSE,
        capability_id="abr_decode_plus_hash",
        composes_tasks=["gap_1", "seed_2"],
    ),

    # ── Regress task (re-test gap_1 with different data) ─────────
    Task(
        id="regress_1",
        description=(
            f"Decode this ABR data (same format as before):\n\n"
            f"Data: {_encode_abr([{'item': 'pen', 'price': '1.50'}, {'item': 'book', 'price': '12.99'}])}\n\n"
            "Return as JSON array."
        ),
        task_type=TaskType.REGRESS,
        capability_id="abr_binary_decode",
        reuses_task="gap_1",
        expected=[{"item": "pen", "price": "1.50"}, {"item": "book", "price": "12.99"}],
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Decode this ABR data. WARNING: some field values may contain bytes "
            "that look like delimiters (0xFF) or null bytes. Handle encoding edge cases.\n\n"
            f"Data: {ABR_ESCAPED}\n\n"
            "Return as JSON array of objects."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="abr_binary_decode",
        breaks_task="gap_1",
    ),
    Task(
        id="adversarial_2",
        description=(
            "Parse this RLE matrix. Note: contains zero-length runs, negative values, "
            "and large values.\n\n"
            f"Data: {RLE_ADVERSARIAL}\n\n"
            "Return as list of lists."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="rle_decompress",
        breaks_task="gap_2",
        expected=MATRIX_ADVERSARIAL,
    ),
]


def create_session() -> Session:
    return Session(
        id="data_transform_s1",
        name="Proprietary Format Processing (ABR + RLE)",
        domain="data_transform",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description="Tests tool creation for custom binary formats that cannot be solved "
                    "from LLM training data. Agent MUST create and execute tools.",
    )
