"""Domain A, Session 5: Custom Checksum & Integrity Format (GUARDIAN blocks).

Key design principle: tasks use CUSTOM ENCODINGS that the LLM cannot
solve from training data. The agent MUST create and execute tools.

GUARDIAN (Guarded Data Integrity Archive) block format:
  - Data is split into fixed-size blocks (default 16 bytes)
  - Each block is encoded as:
    [2-byte block_id big-endian]
    [1-byte data_length]  (actual data bytes in this block, <= block_size)
    [data bytes, padded to block_size with 0x00]
    [2-byte CRC-16/CCITT checksum of the unpadded data]
    [1-byte parity byte: XOR of all data bytes]
  - After all data blocks, there are parity blocks for error correction:
    [2-byte block_id = 0xFFnn where nn = parity group index]
    [1-byte = block_size]
    [block_size bytes: XOR of all data blocks in the parity group]
    [2-byte CRC of the parity data]
    [1-byte = 0x00 (unused)]
  - Parity groups: blocks are grouped by (block_id % parity_group_size)
  - File header (6 bytes):
    [2-byte magic = 0x47 0x44 ("GD")]
    [1-byte version = 0x01]
    [1-byte block_size]
    [1-byte parity_group_size]
    [1-byte total_data_blocks]
  - Entire payload is base64-encoded for transport

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (read_csv, write_json, compute_hash)
  Gap 1:     Decode and verify GUARDIAN block integrity (check CRC + parity)
  Gap 2:     Repair corrupted blocks using parity data
  Variant 1: Decode different GUARDIAN data — should REUSE gap_1
  Variant 2: Repair different corrupted data — should REUSE gap_2
  Compose 1: Decode, verify, and repair in one pipeline
  Regress 1: Re-decode original GUARDIAN data
  Adversarial 1: Data with multiple corrupted blocks in same parity group
  Adversarial 2: Edge case: single-block data, max block size, empty payload
"""

import base64
import struct
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── CRC-16/CCITT implementation ─────────────────────────────────────

def _crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT (XModem variant) — poly 0x1021, init 0xFFFF."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


# ── GUARDIAN Format Encoder ──────────────────────────────────────────

def _encode_guardian(
    data: bytes,
    block_size: int = 16,
    parity_group_size: int = 3,
) -> str:
    """Encode data into GUARDIAN block format, return base64."""
    # Split data into blocks
    blocks = []
    for i in range(0, len(data), block_size):
        chunk = data[i:i + block_size]
        blocks.append(chunk)

    total_data_blocks = len(blocks)
    buf = bytearray()

    # Header
    buf.extend(b'\x47\x44')          # magic "GD"
    buf.append(0x01)                  # version
    buf.append(block_size)
    buf.append(parity_group_size)
    buf.append(total_data_blocks)

    # Data blocks
    for block_id, chunk in enumerate(blocks):
        data_len = len(chunk)
        padded = chunk + b'\x00' * (block_size - data_len)
        crc = _crc16_ccitt(chunk)     # CRC of unpadded data
        parity_byte = 0
        for b in chunk:
            parity_byte ^= b

        buf.extend(struct.pack('>H', block_id))
        buf.append(data_len)
        buf.extend(padded)
        buf.extend(struct.pack('>H', crc))
        buf.append(parity_byte)

    # Parity blocks — XOR of all blocks in each parity group
    num_parity_groups = parity_group_size  # groups 0..parity_group_size-1
    for group_idx in range(num_parity_groups):
        parity_data = bytearray(block_size)
        group_blocks = [i for i in range(total_data_blocks) if i % parity_group_size == group_idx]
        for bid in group_blocks:
            chunk = blocks[bid]
            padded = chunk + b'\x00' * (block_size - len(chunk))
            for j in range(block_size):
                parity_data[j] ^= padded[j]

        parity_crc = _crc16_ccitt(bytes(parity_data))
        buf.extend(struct.pack('>H', 0xFF00 | group_idx))
        buf.append(block_size)
        buf.extend(parity_data)
        buf.extend(struct.pack('>H', parity_crc))
        buf.append(0x00)

    return base64.b64encode(bytes(buf)).decode('ascii')


def _corrupt_block(b64_data: str, block_id: int, corrupt_byte_offset: int = 0) -> str:
    """Corrupt a single byte in a specific data block for testing repair."""
    raw = bytearray(base64.b64decode(b64_data))
    # Parse header
    block_size = raw[3]
    # Each data block: 2 (id) + 1 (len) + block_size + 2 (crc) + 1 (parity) = block_size + 6
    block_total = block_size + 6
    header_size = 6
    block_start = header_size + block_id * block_total
    data_offset = block_start + 3  # skip id (2) + len (1)

    # Flip a byte in the data
    raw[data_offset + corrupt_byte_offset] ^= 0xAA

    # Recompute CRC with corrupted data (to make it a detectable corruption)
    # Actually, we want the CRC to NOT match, so don't recompute
    return base64.b64encode(bytes(raw)).decode('ascii')


def _decode_guardian(b64_data: str) -> dict:
    """Reference decoder for GUARDIAN format."""
    raw = base64.b64decode(b64_data)
    if len(raw) < 6 or raw[0:2] != b'\x47\x44':
        raise ValueError("Invalid GUARDIAN header")

    version = raw[2]
    block_size = raw[3]
    parity_group_size = raw[4]
    total_data_blocks = raw[5]

    block_total = block_size + 6  # id(2) + len(1) + data(block_size) + crc(2) + parity(1)
    offset = 6

    data_blocks = {}
    parity_blocks = {}
    integrity_results = []

    # Read data blocks
    for _ in range(total_data_blocks):
        if offset + block_total > len(raw):
            break
        block_id = struct.unpack('>H', raw[offset:offset + 2])[0]
        data_len = raw[offset + 2]
        block_data = raw[offset + 3:offset + 3 + data_len]
        padded_data = raw[offset + 3:offset + 3 + block_size]
        stored_crc = struct.unpack('>H', raw[offset + 3 + block_size:offset + 5 + block_size])[0]
        stored_parity = raw[offset + 5 + block_size]

        computed_crc = _crc16_ccitt(block_data)
        computed_parity = 0
        for b in block_data:
            computed_parity ^= b

        crc_ok = computed_crc == stored_crc
        parity_ok = computed_parity == stored_parity

        data_blocks[block_id] = {
            "data": bytes(padded_data),
            "data_len": data_len,
            "crc_ok": crc_ok,
            "parity_ok": parity_ok,
        }
        integrity_results.append({
            "block_id": block_id,
            "crc_valid": crc_ok,
            "parity_valid": parity_ok,
        })
        offset += block_total

    # Read parity blocks
    while offset + block_total <= len(raw):
        block_id = struct.unpack('>H', raw[offset:offset + 2])[0]
        if (block_id & 0xFF00) != 0xFF00:
            break
        group_idx = block_id & 0xFF
        parity_len = raw[offset + 2]
        parity_data = raw[offset + 3:offset + 3 + parity_len]
        parity_blocks[group_idx] = bytes(parity_data)
        offset += block_total

    # Reconstruct data
    reconstructed = bytearray()
    for bid in range(total_data_blocks):
        block = data_blocks.get(bid)
        if block:
            reconstructed.extend(block["data"][:block["data_len"]])

    return {
        "data": bytes(reconstructed),
        "text": reconstructed.decode('utf-8', errors='replace'),
        "blocks": total_data_blocks,
        "integrity": integrity_results,
        "parity_groups": len(parity_blocks),
    }


# ── Test Data ────────────────────────────────────────────────────────

TEXT_1 = "Hello, GUARDIAN format! This is a test of integrity checking with CRC-16 and XOR parity."
GUARDIAN_1 = _encode_guardian(TEXT_1.encode('utf-8'), block_size=16, parity_group_size=3)

TEXT_2 = "Short message for variant test with different content."
GUARDIAN_2 = _encode_guardian(TEXT_2.encode('utf-8'), block_size=16, parity_group_size=3)

TEXT_3 = "Repair me! This data has a corrupted block that needs fixing."
GUARDIAN_3_CLEAN = _encode_guardian(TEXT_3.encode('utf-8'), block_size=16, parity_group_size=3)
# Corrupt block 1 (second block)
GUARDIAN_3_CORRUPT = _corrupt_block(GUARDIAN_3_CLEAN, block_id=1, corrupt_byte_offset=2)

TEXT_4 = "Another repair test with different corruption location."
GUARDIAN_4_CLEAN = _encode_guardian(TEXT_4.encode('utf-8'), block_size=16, parity_group_size=3)
GUARDIAN_4_CORRUPT = _corrupt_block(GUARDIAN_4_CLEAN, block_id=2, corrupt_byte_offset=5)

# Adversarial: corrupt two blocks in the SAME parity group (unrepairable with simple XOR)
TEXT_ADV = "This tests double corruption in a parity group which cannot be repaired by XOR alone."
GUARDIAN_ADV_CLEAN = _encode_guardian(TEXT_ADV.encode('utf-8'), block_size=16, parity_group_size=3)
GUARDIAN_ADV_DOUBLE = _corrupt_block(
    _corrupt_block(GUARDIAN_ADV_CLEAN, block_id=0, corrupt_byte_offset=0),
    block_id=3, corrupt_byte_offset=0
)  # blocks 0 and 3 are in the same parity group (0 % 3 == 0, 3 % 3 == 0)

# Single-block edge case
TEXT_TINY = "Hi"
GUARDIAN_TINY = _encode_guardian(TEXT_TINY.encode('utf-8'), block_size=16, parity_group_size=3)

# Expected integrity results for clean data
INTEGRITY_1 = [{"block_id": i, "crc_valid": True, "parity_valid": True}
               for i in range(len(range(0, len(TEXT_1.encode('utf-8')), 16)))]

INTEGRITY_3_CORRUPT = []
_t3_bytes = TEXT_3.encode('utf-8')
for i in range(len(range(0, len(_t3_bytes), 16))):
    if i == 1:
        INTEGRITY_3_CORRUPT.append({"block_id": i, "crc_valid": False, "parity_valid": False})
    else:
        INTEGRITY_3_CORRUPT.append({"block_id": i, "crc_valid": True, "parity_valid": True})


# ── Tasks ────────────────────────────────────────────────────────────

TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Read this CSV and convert it to JSON:\n"
            "block_id,crc_valid,parity_valid\n0,true,true\n1,false,false\n2,true,true"
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description='Compute the SHA-256 hash of "guardian-format-v1".',
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "Read this CSV, then output the data as JSON:\n"
            "group,block_count\n0,2\n1,2\n2,2"
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks (require creating new tools) ───────────────────
    Task(
        id="gap_1",
        description=(
            "Decode and verify this GUARDIAN (Guarded Data Integrity Archive) block format data.\n\n"
            "GUARDIAN format specification:\n"
            "- Base64 encoded binary data\n"
            "- File header (6 bytes):\n"
            "  [2-byte magic = 0x47 0x44 ('GD')]\n"
            "  [1-byte version = 0x01]\n"
            "  [1-byte block_size]\n"
            "  [1-byte parity_group_size]\n"
            "  [1-byte total_data_blocks]\n"
            "- Each data block:\n"
            "  [2-byte block_id big-endian]\n"
            "  [1-byte data_length (actual bytes, <= block_size)]\n"
            "  [data bytes, zero-padded to block_size]\n"
            "  [2-byte CRC-16/CCITT checksum of UNpadded data (poly=0x1021, init=0xFFFF)]\n"
            "  [1-byte XOR parity of all unpadded data bytes]\n"
            "- After data blocks, parity blocks for error correction:\n"
            "  [2-byte block_id = 0xFFnn where nn = parity group index]\n"
            "  [1-byte = block_size]\n"
            "  [block_size bytes: XOR of all padded data blocks in the parity group]\n"
            "  [2-byte CRC of parity data]\n"
            "  [1-byte = 0x00]\n"
            "- Parity grouping: block belongs to group (block_id %% parity_group_size)\n\n"
            f"Data: {GUARDIAN_1}\n\n"
            "Return a dict with:\n"
            "- 'text': the decoded UTF-8 text\n"
            "- 'blocks': total number of data blocks\n"
            "- 'integrity': list of dicts with block_id, crc_valid (bool), parity_valid (bool)\n"
            "All blocks should have valid CRC and parity."
        ),
        task_type=TaskType.GAP,
        capability_id="guardian_decode_verify",
        expected={
            "text": TEXT_1,
            "blocks": len(list(range(0, len(TEXT_1.encode('utf-8')), 16))),
            "integrity": INTEGRITY_1,
        },
        hidden_tests=[
            # v1
            {"input": {"data": GUARDIAN_TINY},
             "expected": {"text": TEXT_TINY, "blocks": 1,
                          "integrity": [{"block_id": 0, "crc_valid": True, "parity_valid": True}]}},
            {"input": {"data": GUARDIAN_3_CORRUPT},
             "verify": "any(not b['crc_valid'] for b in result['integrity']) and result['blocks'] > 0"},
            # v3 expansion
            {"input": {"data": GUARDIAN_1},
             "verify": f"result['text'] == {TEXT_1!r} and all(b['crc_valid'] for b in result['integrity'])"},
            {"input": {"data": _encode_guardian(b'Short text under 16 bytes')},
             "verify": "result['text'] == 'Short text under 16 bytes' and result['blocks'] >= 1"},
            {"input": {"data": _encode_guardian(b'A' * 64)},
             "verify": "result['text'] == 'A' * 64 and result['blocks'] == 4"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"data": ""}},
            {"input": {"data": base64.b64encode(b'\x47\x44').decode()}},
            {"input": {"data": base64.b64encode(b'\x00\x00\x01\x10\x03\x00').decode()}},
            # v3 expansion
            {"input": {"data": "!!!not-base64!!!"}},
            {"input": {"data": base64.b64encode(b'\x47\x44\x01\x10\xff\xff').decode()}},  # impossible block count
            {"input": {"data": base64.b64encode(b'\x47\x44' + b'\x00' * 100).decode()}},   # header ok, junk body
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Repair a corrupted GUARDIAN block using parity data.\n\n"
            "Given GUARDIAN data with one corrupted block (CRC mismatch), use the XOR parity block "
            "for that block's parity group to reconstruct the correct data.\n\n"
            "Repair algorithm:\n"
            "1. Find the corrupted block (CRC mismatch)\n"
            "2. Determine its parity group: group = block_id %% parity_group_size\n"
            "3. XOR the parity block with all OTHER valid blocks in the same group\n"
            "4. The result is the original data for the corrupted block\n"
            "5. Verify the repaired block's CRC matches\n\n"
            f"Corrupted data: {GUARDIAN_3_CORRUPT}\n\n"
            "Return a dict with:\n"
            "- 'repaired_text': the fully repaired UTF-8 text\n"
            "- 'corrupted_blocks': list of block_ids that were corrupted\n"
            "- 'repair_success': True if all blocks now pass CRC"
        ),
        task_type=TaskType.GAP,
        capability_id="guardian_block_repair",
        expected={
            "repaired_text": TEXT_3,
            "corrupted_blocks": [1],
            "repair_success": True,
        },
        hidden_tests=[
            # v1
            {"input": {"data": GUARDIAN_4_CORRUPT},
             "expected": {"repaired_text": TEXT_4, "corrupted_blocks": [2], "repair_success": True}},
            {"input": {"data": GUARDIAN_1},
             "expected": {"repaired_text": TEXT_1, "corrupted_blocks": [], "repair_success": True}},
            # v3 expansion (use uncorrupted reference data for verifiability)
            {"input": {"data": _encode_guardian(b'Plain undamaged input data here')},
             "verify": "result['corrupted_blocks'] == [] and result['repair_success'] is True"},
            {"input": {"data": _encode_guardian(b'Another clean payload XXX')},
             "verify": "result['repair_success'] is True"},
            {"input": {"data": _corrupt_block(_encode_guardian(b'Sixteen bytes a' * 3), block_id=0)},
             "verify": "0 in result['corrupted_blocks']"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"data": ""}},
            {"input": {"data": GUARDIAN_ADV_DOUBLE}},
            # v3 expansion
            {"input": {"data": "!!!not-base64!!!"}},
            {"input": {"data": base64.b64encode(b'\x47\x44\x00\x00').decode()}},   # truncated header
            {"input": {"data": base64.b64encode(b'\x47\x44\x01\x10\x00\x00').decode()}},  # zero blocks
        ],
    ),

    # ── Variant tasks (should REUSE gap tools) ───────────────────
    Task(
        id="variant_1",
        description=(
            "Decode and verify this GUARDIAN data (same format as before):\n\n"
            f"Data: {GUARDIAN_2}\n\n"
            "Return text, blocks count, and integrity results."
        ),
        task_type=TaskType.VARIANT,
        capability_id="guardian_decode_verify",
        reuses_task="gap_1",
        expected={
            "text": TEXT_2,
            "blocks": len(list(range(0, len(TEXT_2.encode('utf-8')), 16))),
            "integrity": [{"block_id": i, "crc_valid": True, "parity_valid": True}
                          for i in range(len(list(range(0, len(TEXT_2.encode('utf-8')), 16))))],
        },
    ),
    Task(
        id="variant_2",
        description=(
            "Repair this corrupted GUARDIAN data (same format as before):\n\n"
            f"Corrupted data: {GUARDIAN_4_CORRUPT}\n\n"
            "Return repaired text, corrupted block IDs, and repair success status."
        ),
        task_type=TaskType.VARIANT,
        capability_id="guardian_block_repair",
        reuses_task="gap_2",
        expected={
            "repaired_text": TEXT_4,
            "corrupted_blocks": [2],
            "repair_success": True,
        },
    ),

    # ── Compose task (decode + verify + repair pipeline) ──────────
    Task(
        id="compose_1",
        description=(
            "Decode this GUARDIAN data, check integrity, and if any blocks are corrupted, "
            "repair them. Return the final clean text and a summary.\n\n"
            f"Data: {GUARDIAN_3_CORRUPT}\n\n"
            "Return: {{'text': repaired_text, 'was_corrupted': bool, 'blocks_repaired': int}}"
        ),
        task_type=TaskType.COMPOSE,
        capability_id="guardian_decode_verify_repair",
        composes_tasks=["gap_1", "gap_2"],
        expected={
            "text": TEXT_3,
            "was_corrupted": True,
            "blocks_repaired": 1,
        },
    ),

    # ── Regress task ────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            f"Decode and verify this GUARDIAN data (same format as before):\n\n"
            f"Data: {_encode_guardian(b'Regression test: GUARDIAN format still works!', block_size=16, parity_group_size=3)}\n\n"
            "Return text and integrity results."
        ),
        task_type=TaskType.REGRESS,
        capability_id="guardian_decode_verify",
        reuses_task="gap_1",
        expected={
            "text": "Regression test: GUARDIAN format still works!",
            "blocks": 3,
            "integrity": [
                {"block_id": 0, "crc_valid": True, "parity_valid": True},
                {"block_id": 1, "crc_valid": True, "parity_valid": True},
                {"block_id": 2, "crc_valid": True, "parity_valid": True},
            ],
        },
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Decode this GUARDIAN data that has TWO corrupted blocks in the SAME parity group.\n"
            "XOR parity alone cannot repair two corruptions in the same group.\n\n"
            "Your tool should:\n"
            "1. Detect both corrupted blocks\n"
            "2. Attempt repair — it should fail or report partial repair\n"
            "3. Return repair_success=False when multiple blocks in one group are corrupted\n\n"
            f"Data: {GUARDIAN_ADV_DOUBLE}\n\n"
            "Return corrupted_blocks list and repair_success status."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="guardian_block_repair",
        breaks_task="gap_2",
        expected={
            "corrupted_blocks": [0, 3],
            "repair_success": False,
        },
    ),
    Task(
        id="adversarial_2",
        description=(
            "Decode this minimal GUARDIAN data (single block, only 2 bytes of actual data):\n\n"
            f"Data: {GUARDIAN_TINY}\n\n"
            "Edge cases to handle:\n"
            "- Single data block (block_size=16 but only 2 bytes of data)\n"
            "- Padding bytes should NOT be included in output\n"
            "- Parity group with only one block\n\n"
            "Return the decoded text and verify integrity."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="guardian_decode_verify",
        breaks_task="gap_1",
        expected={
            "text": TEXT_TINY,
            "blocks": 1,
            "integrity": [{"block_id": 0, "crc_valid": True, "parity_valid": True}],
        },
    ),
]


def create_session() -> Session:
    return Session(
        id="data_transform_s5",
        name="Custom Checksum & Integrity Format (GUARDIAN)",
        domain="data_transform",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description="Tests tool creation for decoding and repairing a custom integrity format "
                    "(GUARDIAN blocks) with CRC-16 and XOR parity. Agent MUST create and execute tools.",
    )
