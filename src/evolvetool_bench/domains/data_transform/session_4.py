"""Domain A, Session 4: Custom Serialization Format (TPACK — Tagged Pack Format).

Key design principle: tasks use CUSTOM ENCODINGS that the LLM cannot
solve from training data. The agent MUST create and execute tools.

TPACK (Tagged Pack Format) is a custom compact serialization format:
  - Every value starts with a 1-byte type tag
  - Type tags:
    0x01 = null
    0x02 = boolean false
    0x03 = boolean true
    0x10 = uint8  (1 byte follows)
    0x11 = uint16 (2 bytes big-endian follow)
    0x12 = int32  (4 bytes big-endian follow)
    0x13 = float64 (8 bytes IEEE 754 big-endian follow)
    0x20 = string (varint length + UTF-8 bytes)
    0x30 = array  (varint count + elements)
    0x40 = map    (varint count + key-value pairs, keys are always strings)
  - Varint encoding: 7 bits per byte, MSB=1 means more bytes follow
    (similar to protobuf varints but custom — value is little-endian within groups)
  - Top-level value is always a map or array
  - Entire payload is base64-encoded for transport

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (read_csv, write_json, compute_hash)
  Gap 1:     Deserialize TPACK format into Python dicts/lists
  Gap 2:     Query/filter deserialized TPACK data
  Variant 1: Deserialize different TPACK data — should REUSE gap_1
  Variant 2: Different query on different data — should REUSE gap_2
  Compose 1: Deserialize TPACK then query the result
  Regress 1: Re-deserialize original TPACK data
  Adversarial 1: TPACK with deeply nested structures and large varints
  Adversarial 2: Query with missing keys and type mismatches
"""

import base64
import struct
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── TPACK Format Encoder ────────────────────────────────────────────

def _encode_varint(n: int) -> bytes:
    """Encode an unsigned integer as a TPACK varint."""
    if n < 0:
        raise ValueError("Varint must be non-negative")
    result = bytearray()
    while n >= 0x80:
        result.append((n & 0x7F) | 0x80)
        n >>= 7
    result.append(n & 0x7F)
    return bytes(result)


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Decode a TPACK varint. Returns (value, new_offset)."""
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, offset


def _tpack_encode(value) -> bytes:
    """Encode a Python value into TPACK binary format."""
    if value is None:
        return b'\x01'
    elif isinstance(value, bool):
        return b'\x03' if value else b'\x02'
    elif isinstance(value, int):
        if 0 <= value <= 255:
            return b'\x10' + struct.pack('B', value)
        elif 0 <= value <= 65535:
            return b'\x11' + struct.pack('>H', value)
        else:
            return b'\x12' + struct.pack('>i', value)
    elif isinstance(value, float):
        return b'\x13' + struct.pack('>d', value)
    elif isinstance(value, str):
        encoded = value.encode('utf-8')
        return b'\x20' + _encode_varint(len(encoded)) + encoded
    elif isinstance(value, list):
        buf = bytearray(b'\x30')
        buf.extend(_encode_varint(len(value)))
        for item in value:
            buf.extend(_tpack_encode(item))
        return bytes(buf)
    elif isinstance(value, dict):
        buf = bytearray(b'\x40')
        buf.extend(_encode_varint(len(value)))
        for k, v in value.items():
            # Keys are always strings
            k_bytes = str(k).encode('utf-8')
            buf.extend(_encode_varint(len(k_bytes)))
            buf.extend(k_bytes)
            buf.extend(_tpack_encode(v))
        return bytes(buf)
    else:
        raise TypeError(f"Unsupported type: {type(value)}")


def _tpack_decode(data: bytes, offset: int = 0) -> tuple:
    """Decode a TPACK value. Returns (value, new_offset)."""
    if offset >= len(data):
        raise ValueError("Unexpected end of data")

    tag = data[offset]
    offset += 1

    if tag == 0x01:
        return None, offset
    elif tag == 0x02:
        return False, offset
    elif tag == 0x03:
        return True, offset
    elif tag == 0x10:
        return data[offset], offset + 1
    elif tag == 0x11:
        val = struct.unpack('>H', data[offset:offset + 2])[0]
        return val, offset + 2
    elif tag == 0x12:
        val = struct.unpack('>i', data[offset:offset + 4])[0]
        return val, offset + 4
    elif tag == 0x13:
        val = struct.unpack('>d', data[offset:offset + 8])[0]
        return val, offset + 8
    elif tag == 0x20:
        length, offset = _decode_varint(data, offset)
        val = data[offset:offset + length].decode('utf-8')
        return val, offset + length
    elif tag == 0x30:
        count, offset = _decode_varint(data, offset)
        result = []
        for _ in range(count):
            item, offset = _tpack_decode(data, offset)
            result.append(item)
        return result, offset
    elif tag == 0x40:
        count, offset = _decode_varint(data, offset)
        result = {}
        for _ in range(count):
            key_len, offset = _decode_varint(data, offset)
            key = data[offset:offset + key_len].decode('utf-8')
            offset += key_len
            val, offset = _tpack_decode(data, offset)
            result[key] = val
        return result, offset
    else:
        raise ValueError(f"Unknown tag: 0x{tag:02x}")


def _encode_tpack_b64(value) -> str:
    """Encode a value to TPACK and return as base64."""
    return base64.b64encode(_tpack_encode(value)).decode('ascii')


def _decode_tpack_b64(b64_data: str):
    """Decode base64 TPACK data."""
    raw = base64.b64decode(b64_data)
    value, _ = _tpack_decode(raw)
    return value


# ── Test Data ────────────────────────────────────────────────────────

USERS_DATA = [
    {"name": "Alice", "age": 30, "active": True, "score": 95.5, "role": "admin"},
    {"name": "Bob", "age": 25, "active": False, "score": 72.0, "role": "viewer"},
    {"name": "Charlie", "age": 35, "active": True, "score": 88.3, "role": "editor"},
]
TPACK_USERS = _encode_tpack_b64(USERS_DATA)

PRODUCTS_DATA = [
    {"sku": "WDG-001", "name": "Widget", "price": 9.99, "qty": 100, "available": True},
    {"sku": "GDG-002", "name": "Gadget", "price": 24.99, "qty": 50, "available": True},
    {"sku": "GZM-003", "name": "Gizmo", "price": 4.99, "qty": 0, "available": False},
    {"sku": "THG-004", "name": "Thingamajig", "price": 149.99, "qty": 12, "available": True},
]
TPACK_PRODUCTS = _encode_tpack_b64(PRODUCTS_DATA)

ORDERS_DATA = {
    "order_id": "ORD-2025-0042",
    "customer": {"name": "Diana", "email": "diana@test.com"},
    "items": [
        {"sku": "WDG-001", "qty": 3, "unit_price": 9.99},
        {"sku": "GDG-002", "qty": 1, "unit_price": 24.99},
    ],
    "total": 54.96,
    "shipped": False,
    "notes": None,
}
TPACK_ORDERS = _encode_tpack_b64(ORDERS_DATA)

# Deeply nested adversarial data
NESTED_DATA = {
    "level1": {
        "level2": {
            "level3": {
                "level4": {
                    "value": 42,
                    "tags": ["deep", "nested", "test"],
                },
            },
        },
    },
    "big_number": 70000,  # requires uint16 or larger
    "negative": -100,     # requires int32
    "empty_map": {},
    "empty_array": [],
    "long_string": "A" * 200,  # varint length > 127, needs 2-byte varint
}
TPACK_NESTED = _encode_tpack_b64(NESTED_DATA)

# Small single-record test
SINGLE_RECORD = {"x": 1, "y": "hello"}
TPACK_SINGLE = _encode_tpack_b64(SINGLE_RECORD)

# Query results
ACTIVE_USERS = [
    {"name": "Alice", "age": 30, "active": True, "score": 95.5, "role": "admin"},
    {"name": "Charlie", "age": 35, "active": True, "score": 88.3, "role": "editor"},
]

EXPENSIVE_PRODUCTS = [
    {"sku": "GDG-002", "name": "Gadget", "price": 24.99, "qty": 50, "available": True},
    {"sku": "THG-004", "name": "Thingamajig", "price": 149.99, "qty": 12, "available": True},
]

AVAILABLE_PRODUCTS = [
    {"sku": "WDG-001", "name": "Widget", "price": 9.99, "qty": 100, "available": True},
    {"sku": "GDG-002", "name": "Gadget", "price": 24.99, "qty": 50, "available": True},
    {"sku": "THG-004", "name": "Thingamajig", "price": 149.99, "qty": 12, "available": True},
]


# ── Tasks ────────────────────────────────────────────────────────────

TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Read this CSV and convert it to JSON:\n"
            "tag,type,size\n0x10,uint8,1\n0x11,uint16,2\n0x12,int32,4\n0x13,float64,8"
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description='Compute the SHA-256 hash of "tpack-format-v1".',
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "Read this CSV, then output the data as JSON:\n"
            "name,active,score\nAlice,true,95.5\nBob,false,72.0\nCharlie,true,88.3"
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks (require creating new tools) ───────────────────
    Task(
        id="gap_1",
        description=(
            "Deserialize this TPACK (Tagged Pack Format) binary data into Python objects.\n\n"
            "TPACK format specification:\n"
            "- Base64 encoded binary data\n"
            "- Every value starts with a 1-byte type tag:\n"
            "  0x01=null, 0x02=false, 0x03=true\n"
            "  0x10=uint8 (1 byte), 0x11=uint16 (2 bytes big-endian)\n"
            "  0x12=int32 (4 bytes big-endian), 0x13=float64 (8 bytes IEEE 754 big-endian)\n"
            "  0x20=string (varint length + UTF-8 bytes)\n"
            "  0x30=array (varint count + elements)\n"
            "  0x40=map (varint count + key-value pairs, keys are always strings)\n"
            "- Varint: 7 bits per byte, MSB=1 means more bytes follow (little-endian bit groups)\n\n"
            f"Data: {TPACK_USERS}\n\n"
            "Return the deserialized Python data structure."
        ),
        task_type=TaskType.GAP,
        capability_id="tpack_deserialize",
        expected=USERS_DATA,
        hidden_tests=[
            # v1
            {"input": {"data": TPACK_SINGLE}, "expected": SINGLE_RECORD},
            {"input": {"data": _encode_tpack_b64([1, "two", 3.0, None, True])},
             "expected": [1, "two", 3.0, None, True]},
            # v3 expansion
            {"input": {"data": _encode_tpack_b64({"key": "value", "num": 42})},
             "expected": {"key": "value", "num": 42}},
            {"input": {"data": _encode_tpack_b64([])},
             "expected": []},
            {"input": {"data": _encode_tpack_b64([{"a": 1}, {"a": 2}, {"a": 3}])},
             "expected": [{"a": 1}, {"a": 2}, {"a": 3}]},
        ],
        adversarial_tests=[
            # v1
            {"input": {"data": ""}},
            {"input": {"data": "AQ=="}},
            {"input": {"data": base64.b64encode(b'\xFF').decode()}},
            # v3 expansion
            {"input": {"data": "not-base64-at-all"}},
            {"input": {"data": base64.b64encode(b'\x05\x80\x80\x80\x80').decode()}},   # malformed varint
            {"input": {"data": base64.b64encode(b'\x06\x10unfinished').decode()}},     # truncated string payload
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Query/filter deserialized TPACK data. Given this list of user records:\n\n"
            f"{USERS_DATA}\n\n"
            "Filter to only records where 'active' is True.\n"
            "Return the matching records."
        ),
        task_type=TaskType.GAP,
        capability_id="tpack_record_query",
        expected=ACTIVE_USERS,
        hidden_tests=[
            # v1
            {"input": {"records": PRODUCTS_DATA, "filter_field": "available", "filter_value": True},
             "expected": AVAILABLE_PRODUCTS},
            {"input": {"records": USERS_DATA, "filter_field": "role", "filter_value": "admin"},
             "expected": [USERS_DATA[0]]},
            # v3 expansion
            {"input": {"records": USERS_DATA, "filter_field": "active", "filter_value": False},
             "verify": "all(not r['active'] for r in result)"},
            {"input": {"records": USERS_DATA, "filter_field": "role", "filter_value": "user"},
             "verify": "len(result) >= 1 and all(r['role'] == 'user' for r in result)"},
            {"input": {"records": [{"x": 1}, {"x": 2}, {"x": 1}], "filter_field": "x", "filter_value": 1},
             "expected": [{"x": 1}, {"x": 1}]},
        ],
        adversarial_tests=[
            # v1
            {"input": {"records": [], "filter_field": "active", "filter_value": True}},
            {"input": {"records": USERS_DATA, "filter_field": "nonexistent", "filter_value": True}},
            {"input": {"records": [{"a": None}], "filter_field": "a", "filter_value": None}},
            # v3 expansion
            {"input": {"records": None, "filter_field": "x", "filter_value": 1}},
            {"input": {"records": "not a list", "filter_field": "x", "filter_value": 1}},
            {"input": {"records": [{"x": 1}], "filter_field": None, "filter_value": 1}},
        ],
    ),

    # ── Variant tasks (should REUSE gap tools) ───────────────────
    Task(
        id="variant_1",
        description=(
            "Deserialize this TPACK data (same format as before):\n\n"
            f"Data: {TPACK_PRODUCTS}\n\n"
            "Return the deserialized data."
        ),
        task_type=TaskType.VARIANT,
        capability_id="tpack_deserialize",
        reuses_task="gap_1",
        expected=PRODUCTS_DATA,
    ),
    Task(
        id="variant_2",
        description=(
            "Filter these product records to only those with price > 10.0:\n\n"
            f"{PRODUCTS_DATA}\n\n"
            "Return matching records."
        ),
        task_type=TaskType.VARIANT,
        capability_id="tpack_record_query",
        reuses_task="gap_2",
        expected=EXPENSIVE_PRODUCTS,
    ),

    # ── Compose task (deserialize then query) ─────────────────────
    Task(
        id="compose_1",
        description=(
            "Deserialize this TPACK data, then filter the resulting records "
            "to only those where 'available' is True.\n\n"
            f"Data: {TPACK_PRODUCTS}\n\n"
            "Return the filtered records."
        ),
        task_type=TaskType.COMPOSE,
        capability_id="tpack_deserialize_plus_query",
        composes_tasks=["gap_1", "gap_2"],
        expected=AVAILABLE_PRODUCTS,
    ),

    # ── Regress task ────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            f"Deserialize this TPACK data (same format as before):\n\n"
            f"Data: {TPACK_ORDERS}\n\n"
            "Return the deserialized data."
        ),
        task_type=TaskType.REGRESS,
        capability_id="tpack_deserialize",
        reuses_task="gap_1",
        expected=ORDERS_DATA,
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Deserialize this TPACK data that contains:\n"
            "- Deeply nested maps (4 levels deep)\n"
            "- A number > 255 (requires uint16 encoding)\n"
            "- A negative number (requires int32 encoding)\n"
            "- Empty maps and arrays\n"
            "- A string > 127 bytes (requires multi-byte varint for length)\n\n"
            f"Data: {TPACK_NESTED}\n\n"
            "Return the deserialized data."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="tpack_deserialize",
        breaks_task="gap_1",
        expected=NESTED_DATA,
    ),
    Task(
        id="adversarial_2",
        description=(
            "Query this deserialized TPACK data (a single order object, not an array).\n"
            "Extract all item SKUs from the nested 'items' array.\n\n"
            f"{ORDERS_DATA}\n\n"
            "Return a list of SKU strings: ['WDG-001', 'GDG-002']"
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="tpack_record_query",
        breaks_task="gap_2",
        expected=["WDG-001", "GDG-002"],
    ),
]


def create_session() -> Session:
    return Session(
        id="data_transform_s4",
        name="Custom Serialization Format (TPACK)",
        domain="data_transform",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description="Tests tool creation for deserializing a custom tagged binary format "
                    "(TPACK) with varints and type tags. Agent MUST create and execute tools.",
    )
