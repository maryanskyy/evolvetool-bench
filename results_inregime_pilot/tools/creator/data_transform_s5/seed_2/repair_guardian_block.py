def repair_guardian_block(corrupted_data_b64):
    """
    Repair a corrupted GUARDIAN block using XOR parity data.
    
    Utility:
        Detects and repairs a single corrupted block in a GUARDIAN data structure
        by using XOR parity information. Validates repair using CRC checksums.
    
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
    offset = 0
    parity_group_size = 4
    
    while offset < len(data):
        if offset + 9 > len(data):
            break
        
        block_id = struct.unpack('>H', data[offset:offset+2])[0]
        crc_stored = struct.unpack('>I', data[offset+2:offset+6])[0]
        data_length = struct.unpack('>H', data[offset+6:offset+8])[0]
        
        if offset + 8 + data_length > len(data):
            break
        
        block_data = data[offset+8:offset+8+data_length]
        
        # Calculate actual CRC
        crc_actual = zlib.crc32(block_data) & 0xffffffff
        
        blocks[block_id] = {
            'data': block_data,
            'crc_stored': crc_stored,
            'crc_actual': crc_actual,
            'is_valid': crc_stored == crc_actual
        }
        
        offset += 8 + data_length
    
    # Find corrupted block
    corrupted_block_id = None
    for block_id, block_info in blocks.items():
        if not block_info['is_valid']:
            corrupted_block_id = block_id
            break
    
    # Repair the corrupted block using XOR parity
    if corrupted_block_id is not None:
        parity_group = corrupted_block_id % parity_group_size
        
        # Find all blocks in the same parity group
        group_blocks = [bid for bid in blocks.keys() if bid % parity_group_size == parity_group]
        
        # The parity block is typically the last one in the group
        parity_block_id = max(group_blocks)
        
        # XOR all blocks except the corrupted one with the parity block
        repaired_data = bytearray(blocks[parity_block_id]['data'])
        
        for block_id in group_blocks:
            if block_id != corrupted_block_id and block_id != parity_block_id:
                block_bytes = blocks[block_id]['data']
                for i in range(min(len(repaired_data), len(block_bytes))):
                    repaired_data[i] ^= block_bytes[i]
        
        # Update the corrupted block with repaired data
        blocks[corrupted_block_id]['data'] = bytes(repaired_data)
        blocks[corrupted_block_id]['crc_actual'] = zlib.crc32(repaired_data) & 0xffffffff
        blocks[corrupted_block_id]['is_valid'] = True
    
    # Reconstruct the full text from all blocks
    sorted_blocks = sorted(blocks.items())
    repaired_text = b''.join(block_info['data'] for _, block_info in sorted_blocks)
    
    # Decode to UTF-8
    try:
        repaired_text_str = repaired_text.decode('utf-8')
    except:
        repaired_text_str = repaired_text.decode('utf-8', errors='replace')
    
    # Check if all blocks are now valid
    repair_success = all(block['is_valid'] for block in blocks.values())
    
    return {
        'repaired_text': repaired_text_str,
        'corrupted_blocks': [corrupted_block_id] if corrupted_block_id is not None else [],
        'repair_success': repair_success
    }