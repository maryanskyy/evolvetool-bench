"""Hand-crafted reference implementations for data_transform session 5 gap tasks.

These prove the held-out conformance suites (hidden_tests) are passable by a
correct implementation. Each entry's ``implementation`` is a self-contained
Python source string executed in a bare subprocess by the tool-quality
evaluator; the function is called with **input kwargs and its return value is
JSON-round-tripped before comparison, so outputs use only JSON-safe types and
contain exactly the expected keys.
"""

GUARDIAN_DECODE_VERIFY_IMPL = '''\
def guardian_decode_verify(data: str) -> dict:
    """Decode GUARDIAN block-format data and verify per-block CRC-16/CCITT and XOR parity.

    Returns {'text': str, 'blocks': int, 'integrity': [{'block_id', 'crc_valid', 'parity_valid'}]}.
    On malformed input returns {'error': str} instead of raising.
    """
    import base64
    import struct

    def crc16(payload: bytes) -> int:
        crc = 0xFFFF
        for byte in payload:
            crc ^= byte << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
                crc &= 0xFFFF
        return crc

    try:
        raw = base64.b64decode(data, validate=True)
        if len(raw) < 6 or raw[0:2] != b"GD":
            return {"error": "invalid GUARDIAN header"}
        block_size = raw[3]
        total_data_blocks = raw[5]
        block_total = block_size + 6  # id(2) + len(1) + data + crc(2) + parity(1)

        offset = 6
        text_bytes = bytearray()
        integrity = []
        for _ in range(total_data_blocks):
            if block_size == 0 or offset + block_total > len(raw):
                break
            block_id = struct.unpack(">H", raw[offset:offset + 2])[0]
            data_len = min(raw[offset + 2], block_size)
            block_data = raw[offset + 3:offset + 3 + data_len]
            stored_crc = struct.unpack(
                ">H", raw[offset + 3 + block_size:offset + 5 + block_size])[0]
            stored_parity = raw[offset + 5 + block_size]

            parity = 0
            for b in block_data:
                parity ^= b
            integrity.append({
                "block_id": block_id,
                "crc_valid": crc16(block_data) == stored_crc,
                "parity_valid": parity == stored_parity,
            })
            text_bytes.extend(block_data)
            offset += block_total

        return {
            "text": text_bytes.decode("utf-8", errors="replace"),
            "blocks": total_data_blocks,
            "integrity": integrity,
        }
    except Exception as exc:
        return {"error": str(exc)}
'''

GUARDIAN_BLOCK_REPAIR_IMPL = '''\
def guardian_block_repair(data: str) -> dict:
    """Repair corrupted GUARDIAN blocks (CRC mismatch) using XOR parity groups.

    Returns {'repaired_text': str, 'corrupted_blocks': [int], 'repair_success': bool}.
    On malformed input returns {'error': str} instead of raising.
    """
    import base64
    import struct

    def crc16(payload: bytes) -> int:
        crc = 0xFFFF
        for byte in payload:
            crc ^= byte << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
                crc &= 0xFFFF
        return crc

    try:
        raw = base64.b64decode(data, validate=True)
        if len(raw) < 6 or raw[0:2] != b"GD":
            return {"error": "invalid GUARDIAN header"}
        block_size = raw[3]
        pgs = raw[4]  # parity_group_size
        total_data_blocks = raw[5]
        block_total = block_size + 6

        offset = 6
        blocks = {}  # block_id -> {padded, data_len, crc}
        for _ in range(total_data_blocks):
            if block_size == 0 or offset + block_total > len(raw):
                break
            block_id = struct.unpack(">H", raw[offset:offset + 2])[0]
            blocks[block_id] = {
                "padded": bytearray(raw[offset + 3:offset + 3 + block_size]),
                "data_len": min(raw[offset + 2], block_size),
                "crc": struct.unpack(
                    ">H", raw[offset + 3 + block_size:offset + 5 + block_size])[0],
            }
            offset += block_total

        parity = {}  # group_idx -> parity bytes
        while offset + block_total <= len(raw) and block_size > 0:
            pid = struct.unpack(">H", raw[offset:offset + 2])[0]
            if (pid & 0xFF00) != 0xFF00:
                break
            parity[pid & 0xFF] = raw[offset + 3:offset + 3 + block_size]
            offset += block_total

        def is_bad(blk: dict) -> bool:
            return crc16(bytes(blk["padded"][:blk["data_len"]])) != blk["crc"]

        corrupted = sorted(bid for bid, blk in blocks.items() if is_bad(blk))

        repair_success = True
        for bid in corrupted:
            group = bid % pgs if pgs else 0
            peers = [o for o in blocks if o != bid and (not pgs or o % pgs == group)]
            if any(is_bad(blocks[o]) for o in peers) or group not in parity:
                repair_success = False  # double corruption in group / no parity block
                continue
            rebuilt = bytearray(parity[group])
            for o in peers:
                for j in range(block_size):
                    rebuilt[j] ^= blocks[o]["padded"][j]
            candidate = bytes(rebuilt[:blocks[bid]["data_len"]])
            if crc16(candidate) == blocks[bid]["crc"]:
                blocks[bid]["padded"] = rebuilt
            else:
                repair_success = False

        repair_success = repair_success and not any(is_bad(b) for b in blocks.values())

        text_bytes = bytearray()
        for bid in sorted(blocks):
            text_bytes.extend(blocks[bid]["padded"][:blocks[bid]["data_len"]])
        return {
            "repaired_text": text_bytes.decode("utf-8", errors="replace"),
            "corrupted_blocks": corrupted,
            "repair_success": repair_success,
        }
    except Exception as exc:
        return {"error": str(exc)}
'''


REFERENCE_IMPLS = {
    "guardian_decode_verify": {
        "session_id": "data_transform_s5",
        "task_id": "gap_1",
        "name": "guardian_decode_verify",
        "implementation": GUARDIAN_DECODE_VERIFY_IMPL,
    },
    "guardian_block_repair": {
        "session_id": "data_transform_s5",
        "task_id": "gap_2",
        "name": "guardian_block_repair",
        "implementation": GUARDIAN_BLOCK_REPAIR_IMPL,
    },
}
