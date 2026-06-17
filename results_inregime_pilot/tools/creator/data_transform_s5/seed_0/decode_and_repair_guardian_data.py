def decode_and_repair_guardian_data(encoded_data):
    """
    Decode GUARDIAN format data, verify integrity, and repair corrupted blocks.
    
    The GUARDIAN format uses base64 encoding with block structure where each block
    contains a header (block_id, checksum) followed by data. Corrupted blocks are
    detected via checksum mismatch and repaired using redundancy or pattern recovery.
    
    Utility:
        Decodes base64-encoded GUARDIAN data, validates block checksums, identifies
        corrupted blocks, attempts repair using context and patterns, and returns
        the cleaned text with corruption statistics.
    
    Args:
        encoded_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: {
            'text': str - the repaired/decoded text,
            'was_corrupted': bool - whether any corruption was detected,
            'blocks_repaired': int - number of blocks that were repaired
        }
    """
    import base64
    import struct
    
    # Decode base64
    try:
        decoded_bytes = base64.b64decode(encoded_data)
    except Exception:
        return {'text': '', 'was_corrupted': True, 'blocks_repaired': 0}
    
    blocks = []
    blocks_repaired = 0
    corrupted_block_ids = set()
    
    # Parse blocks: each block has format [block_id:1][checksum:1][length:2][data:variable]
    offset = 0
    while offset < len(decoded_bytes):
        if offset + 4 > len(decoded_bytes):
            break
        
        block_id = decoded_bytes[offset]
        stored_checksum = decoded_bytes[offset + 1]
        data_length = struct.unpack('>H', decoded_bytes[offset + 2:offset + 4])[0]
        
        if offset + 4 + data_length > len(decoded_bytes):
            break
        
        block_data = decoded_bytes[offset + 4:offset + 4 + data_length]
        
        # Calculate checksum (simple XOR of all bytes)
        calculated_checksum = 0
        for byte in block_data:
            calculated_checksum ^= byte
        calculated_checksum = (calculated_checksum ^ block_id) & 0xFF
        
        # Check integrity
        is_corrupted = (calculated_checksum != stored_checksum)
        
        if is_corrupted:
            corrupted_block_ids.add(block_id)
            blocks_repaired += 1
            # Attempt repair: filter out obvious corruption markers and recover text
            repaired_data = bytearray()
            for byte in block_data:
                # Keep printable ASCII and common characters, skip control chars
                if 32 <= byte <= 126 or byte in [9, 10, 13]:
                    repaired_data.append(byte)
                elif byte > 127:
                    # Try to recover high-bit characters as spaces or skip
                    repaired_data.append(32)  # Replace with space
            block_data = bytes(repaired_data)
        
        blocks.append((block_id, block_data))
        offset += 4 + data_length
    
    # Reconstruct text from blocks (sorted by block_id)
    blocks.sort(key=lambda x: x[0])
    text_parts = []
    for block_id, data in blocks:
        try:
            text_parts.append(data.decode('utf-8', errors='replace'))
        except Exception:
            text_parts.append(data.decode('latin-1', errors='replace'))
    
    final_text = ''.join(text_parts)
    
    return {
        'text': final_text,
        'was_corrupted': len(corrupted_block_ids) > 0,
        'blocks_repaired': blocks_repaired
    }