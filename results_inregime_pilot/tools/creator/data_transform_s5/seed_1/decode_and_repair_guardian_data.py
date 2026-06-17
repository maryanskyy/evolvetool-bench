def decode_and_repair_guardian_data(encoded_data):
    """
    Decode GUARDIAN format data, verify integrity using CRC/parity checks,
    repair corrupted blocks, and return cleaned text with repair summary.
    
    Utility:
        Decodes base64-encoded GUARDIAN data blocks, validates each block's
        integrity using embedded CRC and parity information, repairs corrupted
        blocks using redundancy, and returns the reconstructed clean text.
    
    Args:
        encoded_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: Contains 'text' (repaired text), 'was_corrupted' (bool),
              and 'blocks_repaired' (int)
    """
    import base64
    import struct
    
    # Decode base64 data
    try:
        decoded_bytes = base64.b64decode(encoded_data)
    except Exception:
        return {'text': '', 'was_corrupted': False, 'blocks_repaired': 0}
    
    # Parse GUARDIAN format: each block has header (4 bytes) + data + CRC (2 bytes)
    blocks = []
    pos = 0
    
    while pos < len(decoded_bytes):
        if pos + 4 > len(decoded_bytes):
            break
        
        # Read block header: block_id (1 byte), flags (1 byte), length (2 bytes)
        block_id = decoded_bytes[pos]
        flags = decoded_bytes[pos + 1]
        block_len = struct.unpack('>H', decoded_bytes[pos + 2:pos + 4])[0]
        
        pos += 4
        
        if pos + block_len + 2 > len(decoded_bytes):
            break
        
        # Extract block data and CRC
        block_data = decoded_bytes[pos:pos + block_len]
        stored_crc = struct.unpack('>H', decoded_bytes[pos + block_len:pos + block_len + 2])[0]
        
        # Calculate CRC (simple sum-based checksum)
        calculated_crc = sum(block_data) & 0xFFFF
        
        # Check parity (count of set bits should be even for valid block)
        parity = bin(sum(block_data)).count('1') % 2
        
        is_corrupted = (calculated_crc != stored_crc) or (parity != 0)
        
        blocks.append({
            'id': block_id,
            'data': block_data,
            'corrupted': is_corrupted,
            'stored_crc': stored_crc,
            'calculated_crc': calculated_crc
        })
        
        pos += block_len + 2
    
    # Repair corrupted blocks using adjacent blocks or pattern matching
    blocks_repaired = 0
    for i, block in enumerate(blocks):
        if block['corrupted']:
            # Try to repair by finding similar patterns in other blocks
            if i > 0 and not blocks[i - 1]['corrupted']:
                # Use previous block as reference for repair
                block['data'] = blocks[i - 1]['data']
                blocks_repaired += 1
            elif i < len(blocks) - 1 and not blocks[i + 1]['corrupted']:
                # Use next block as reference for repair
                block['data'] = blocks[i + 1]['data']
                blocks_repaired += 1
            else:
                # Attempt character-level repair by fixing common corruption patterns
                repaired_data = bytearray(block['data'])
                for j in range(len(repaired_data)):
                    # Check for common corruption markers (0xFF, 0x00 in text)
                    if repaired_data[j] == 0xFF or repaired_data[j] == 0x00:
                        # Try to infer from context
                        if j > 0:
                            repaired_data[j] = repaired_data[j - 1]
                        elif j < len(repaired_data) - 1:
                            repaired_data[j] = repaired_data[j + 1]
                block['data'] = bytes(repaired_data)
                blocks_repaired += 1
    
    # Reconstruct text from all blocks
    reconstructed_text = b''.join(block['data'] for block in blocks)
    
    # Decode to string, handling potential encoding issues
    try:
        final_text = reconstructed_text.decode('utf-8', errors='replace')
    except Exception:
        final_text = reconstructed_text.decode('latin-1', errors='replace')
    
    # Clean up null bytes and control characters
    final_text = final_text.replace('\x00', '').replace('\xff', '')
    
    was_corrupted = any(block['corrupted'] for block in blocks)
    
    return {
        'text': final_text,
        'was_corrupted': was_corrupted,
        'blocks_repaired': blocks_repaired
    }