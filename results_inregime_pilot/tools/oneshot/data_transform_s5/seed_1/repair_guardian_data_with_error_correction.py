def repair_guardian_data_with_error_correction(encoded_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    try:
        raw_data = base64.b64decode(encoded_data)
    except Exception:
        return '{"text": "", "was_corrupted": false, "blocks_repaired": 0}'
    
    # Parse GUARDIAN format: [header(1)][block_count(1)][blocks...]
    if len(raw_data) < 2:
        return '{"text": "", "was_corrupted": false, "blocks_repaired": 0}'
    
    header = raw_data[0]
    block_count = raw_data[1]
    
    blocks = []
    corrupted_indices = []
    repaired_count = 0
    offset = 2
    
    # Parse blocks: [type(1)][length(1)][crc(1)][parity(1)][data...]
    for i in range(block_count):
        if offset + 4 > len(raw_data):
            break
        
        block_type = raw_data[offset]
        block_len = raw_data[offset + 1]
        block_crc = raw_data[offset + 2]
        block_parity = raw_data[offset + 3]
        
        if offset + 4 + block_len > len(raw_data):
            break
        
        block_data = raw_data[offset + 4:offset + 4 + block_len]
        
        # Calculate CRC (simple XOR checksum)
        calculated_crc = 0
        for byte in block_data:
            calculated_crc ^= byte
        
        # Calculate parity
        calculated_parity = sum(block_data) & 0xFF
        
        # Check integrity
        is_corrupted = (calculated_crc != block_crc) or (calculated_parity != block_parity)
        
        if is_corrupted:
            corrupted_indices.append(i)
            # Attempt repair using XOR error correction
            if block_len > 0:
                repaired_data = bytearray(block_data)
                for j in range(len(repaired_data)):
                    repaired_data[j] ^= (block_crc ^ calculated_crc)
                blocks.append(bytes(repaired_data))
                repaired_count += 1
            else:
                blocks.append(block_data)
        else:
            blocks.append(block_data)
        
        offset += 4 + block_len
    
    # Reconstruct text from blocks
    text_parts = []
    for block in blocks:
        try:
            text_parts.append(block.decode('utf-8', errors='ignore'))
        except:
            text_parts.append('')
    
    final_text = ''.join(text_parts)
    was_corrupted = len(corrupted_indices) > 0
    
    # Return JSON result
    import json
    result = {
        'text': final_text,
        'was_corrupted': was_corrupted,
        'blocks_repaired': repaired_count
    }
    return json.dumps(result)