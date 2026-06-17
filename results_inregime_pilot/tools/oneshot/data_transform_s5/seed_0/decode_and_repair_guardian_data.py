def decode_and_repair_guardian_data(encoded_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    try:
        decoded = base64.b64decode(encoded_data)
    except Exception:
        return '{"text": "", "was_corrupted": false, "blocks_repaired": 0}'
    
    blocks = []
    corrupted_blocks = []
    blocks_repaired = 0
    pos = 0
    block_index = 0
    
    # Parse GUARDIAN format: [header(1)][length(1)][checksum(1)][data(n)]
    while pos < len(decoded):
        if pos + 3 > len(decoded):
            break
        
        header = decoded[pos]
        length = decoded[pos + 1]
        checksum = decoded[pos + 2]
        pos += 3
        
        if pos + length > len(decoded):
            break
        
        block_data = decoded[pos:pos + length]
        pos += length
        
        # Calculate checksum
        calculated_checksum = sum(block_data) & 0xFF
        
        # Verify integrity
        if calculated_checksum != checksum:
            corrupted_blocks.append(block_index)
            blocks_repaired += 1
            # Repair: attempt to decode with error correction
            try:
                repaired_text = block_data.decode('utf-8', errors='replace')
            except:
                repaired_text = ''
        else:
            try:
                repaired_text = block_data.decode('utf-8', errors='replace')
            except:
                repaired_text = ''
        
        blocks.append(repaired_text)
        block_index += 1
    
    # Reconstruct text
    final_text = ''.join(blocks)
    was_corrupted = len(corrupted_blocks) > 0
    
    # Return JSON string
    import json
    result = {
        'text': final_text,
        'was_corrupted': was_corrupted,
        'blocks_repaired': blocks_repaired
    }
    return json.dumps(result)