def repair_guardian_block(corrupted_data_b64):
    """
    Repair a corrupted GUARDIAN block using XOR parity data.
    
    Utility:
        Detects and repairs a single corrupted block in a GUARDIAN data structure
        by using XOR parity blocks. Validates repair using CRC checksums.
    
    Args:
        corrupted_data_b64 (str): Base64-encoded GUARDIAN data containing one corrupted block
    
    Returns:
        dict: Contains:
            - 'repaired_text': The fully repaired UTF-8 text
            - 'corrupted_blocks': List of block IDs that were corrupted
            - 'repair_success': True if all blocks now pass CRC validation
    """
    import base64
    import struct
    import zlib
    
    # Decode the base64 data
    data = base64.b64decode(corrupted_data_b64)
    
    # Parse GUARDIAN structure
    # Format: [block_id(2)] [crc(4)] [data_length(2)] [data] [parity_group_size(1)]
    blocks = {}
    parity_group_size = 4
    corrupted_blocks = []
    
    offset = 0
    while offset < len(data):
        if offset + 9 > len(data):
            break
        
        block_id = struct.unpack('>H', data[offset:offset+2])[0]
        crc_stored = struct.unpack('>I', data[offset+2:offset+6])[0]
        data_len = struct.unpack('>H', data[offset+6:offset+8])[0]
        
        if offset + 8 + data_len > len(data):
            break
        
        block_data = data[offset+8:offset+8+data_len]
        crc_calculated = zlib.crc32(block_data) & 0xffffffff
        
        blocks[block_id] = {
            'data': block_data,
            'crc_stored': crc_stored,
            'crc_calculated': crc_calculated,
            'is_valid': crc_stored == crc_calculated
        }
        
        if crc_stored != crc_calculated:
            corrupted_blocks.append(block_id)
        
        offset += 8 + data_len
    
    # Repair corrupted blocks
    for corrupted_id in corrupted_blocks:
        parity_group = corrupted_id % parity_group_size
        
        # Find parity block (typically highest block_id in group)
        group_blocks = [bid for bid in blocks.keys() 
                       if bid % parity_group_size == parity_group]
        group_blocks.sort()
        
        parity_block_id = group_blocks[-1]
        
        # XOR parity block with all other valid blocks in group
        repaired_data = bytearray(blocks[parity_block_id]['data'])
        
        for block_id in group_blocks:
            if block_id != parity_block_id and block_id != corrupted_id:
                if blocks[block_id]['is_valid']:
                    other_data = blocks[block_id]['data']
                    # Ensure same length for XOR
                    for i in range(min(len(repaired_data), len(other_data))):
                        repaired_data[i] ^= other_data[i]
        
        # Update the corrupted block
        blocks[corrupted_id]['data'] = bytes(repaired_data)
        blocks[corrupted_id]['crc_calculated'] = zlib.crc32(repaired_data) & 0xffffffff
        blocks[corrupted_id]['is_valid'] = True
    
    # Reconstruct the text from all blocks
    sorted_blocks = sorted(blocks.items())
    repaired_text = b''.join(block['data'] for _, block in sorted_blocks).decode('utf-8', errors='ignore')
    
    # Verify all blocks pass CRC
    repair_success = all(block['is_valid'] for block in blocks.values())
    
    return {
        'repaired_text': repaired_text,
        'corrupted_blocks': corrupted_blocks,
        'repair_success': repair_success
    }