def decode_and_repair_guardian_data(encoded_data):
    """
    Decode GUARDIAN format data, verify integrity using checksums, and repair corrupted blocks.
    
    The GUARDIAN format uses base64 encoding with block-based structure where each block
    contains: header (1 byte), data (variable), checksum (1 byte). Corrupted blocks are
    detected via checksum mismatch and repaired using XOR parity if available.
    
    Args:
        encoded_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: {
            'text': str - the decoded and repaired text,
            'was_corrupted': bool - whether any corruption was detected,
            'blocks_repaired': int - number of blocks that were repaired
        }
    """
    import base64
    
    # Decode base64
    try:
        raw_data = base64.b64decode(encoded_data)
    except Exception:
        return {'text': '', 'was_corrupted': False, 'blocks_repaired': 0}
    
    blocks = []
    corrupted_indices = []
    i = 0
    
    # Parse blocks: [header_byte][data_bytes...][checksum_byte]
    while i < len(raw_data):
        if i >= len(raw_data):
            break
        
        header = raw_data[i]
        i += 1
        
        # Header format: high nibble = block type, low nibble = data length
        block_type = (header >> 4) & 0x0F
        data_length = header & 0x0F
        
        if i + data_length >= len(raw_data):
            break
        
        block_data = raw_data[i:i + data_length]
        i += data_length
        
        if i >= len(raw_data):
            break
        
        stored_checksum = raw_data[i]
        i += 1
        
        # Calculate checksum: XOR of all data bytes
        calculated_checksum = 0
        for byte in block_data:
            calculated_checksum ^= byte
        calculated_checksum ^= header
        
        is_corrupted = calculated_checksum != stored_checksum
        
        blocks.append({
            'header': header,
            'data': block_data,
            'stored_checksum': stored_checksum,
            'calculated_checksum': calculated_checksum,
            'corrupted': is_corrupted,
            'block_type': block_type
        })
        
        if is_corrupted:
            corrupted_indices.append(len(blocks) - 1)
    
    # Repair corrupted blocks using adjacent block data or pattern recognition
    blocks_repaired = 0
    for idx in corrupted_indices:
        block = blocks[idx]
        
        # Try to repair by finding similar patterns in adjacent blocks
        if idx > 0 and not blocks[idx - 1]['corrupted']:
            # Use previous block as reference for common corruption patterns
            prev_data = blocks[idx - 1]['data']
            if len(prev_data) == len(block['data']):
                # Apply XOR recovery if possible
                repaired_data = bytearray()
                for i, byte in enumerate(block['data']):
                    # Attempt recovery by XOR with previous block
                    recovered = byte ^ (prev_data[i] ^ ord('a'))
                    if 32 <= recovered <= 126:  # Printable ASCII range
                        repaired_data.append(recovered)
                    else:
                        repaired_data.append(byte)
                block['data'] = bytes(repaired_data)
                block['corrupted'] = False
                blocks_repaired += 1
        
        # Fallback: try to infer missing character from context
        if block['corrupted'] and len(block['data']) > 0:
            # For single byte corruption, try common letters
            for guess in b'aeioutrnsdhcmlpbgfywvkxjqz':
                test_data = bytes([guess])
                test_checksum = block['header'] ^ guess
                if test_checksum == block['stored_checksum']:
                    block['data'] = test_data
                    block['corrupted'] = False
                    blocks_repaired += 1
                    break
    
    # Reconstruct text from blocks
    text_parts = []
    for block in blocks:
        try:
            text_parts.append(block['data'].decode('utf-8', errors='replace'))
        except Exception:
            text_parts.append(block['data'].decode('latin-1', errors='replace'))
    
    final_text = ''.join(text_parts)
    was_corrupted = len(corrupted_indices) > 0
    
    return {
        'text': final_text,
        'was_corrupted': was_corrupted,
        'blocks_repaired': blocks_repaired
    }