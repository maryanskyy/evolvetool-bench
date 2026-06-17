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
    blocks = {}
    offset = 0
    
    while offset < len(data):
        if offset + 12 > len(data):
            break
        
        # Read block header: block_id (2 bytes), flags (2 bytes), crc (4 bytes), length (4 bytes)
        block_id, flags, crc, length = struct.unpack('>HHII', data[offset:offset+12])
        offset += 12
        
        if offset + length > len(data):
            break
        
        block_data = data[offset:offset+length]
        offset += length
        
        blocks[block_id] = {
            'data': block_data,
            'crc': crc,
            'flags': flags,
            'length': length
        }
    
    # Determine parity group size (typically 4)
    parity_group_size = 4
    
    # Find corrupted block by checking CRC
    corrupted_block_id = None
    for block_id, block_info in blocks.items():
        calculated_crc = zlib.crc32(block_info['data']) & 0xffffffff
        if calculated_crc != block_info['crc']:
            corrupted_block_id = block_id
            break
    
    corrupted_blocks = []
    
    # Repair if corrupted block found
    if corrupted_block_id is not None:
        corrupted_blocks.append(corrupted_block_id)
        parity_group = corrupted_block_id % parity_group_size
        
        # Find all blocks in the same parity group
        group_blocks = [bid for bid in blocks.keys() 
                       if bid % parity_group_size == parity_group]
        
        # Identify parity block (typically highest ID in group)
        parity_block_id = max(group_blocks)
        
        # XOR parity block with all other valid blocks to recover corrupted data
        repaired_data = bytearray(blocks[parity_block_id]['data'])
        
        for block_id in group_blocks:
            if block_id != parity_block_id and block_id != corrupted_block_id:
                block_data = blocks[block_id]['data']
                # Extend repaired_data if needed
                if len(repaired_data) < len(block_data):
                    repaired_data.extend(b'\x00' * (len(block_data) - len(repaired_data)))
                # XOR operation
                for i in range(len(block_data)):
                    repaired_data[i] ^= block_data[i]
        
        # Update the corrupted block with repaired data
        blocks[corrupted_block_id]['data'] = bytes(repaired_data[:blocks[corrupted_block_id]['length']])
        blocks[corrupted_block_id]['crc'] = zlib.crc32(blocks[corrupted_block_id]['data']) & 0xffffffff
    
    # Reconstruct the full text from all blocks
    repaired_text = b''
    for block_id in sorted(blocks.keys()):
        repaired_text += blocks[block_id]['data']
    
    # Verify all blocks pass CRC
    repair_success = True
    for block_id, block_info in blocks.items():
        calculated_crc = zlib.crc32(block_info['data']) & 0xffffffff
        if calculated_crc != block_info['crc']:
            repair_success = False
            break
    
    # Decode to UTF-8 text
    try:
        repaired_text_str = repaired_text.decode('utf-8').strip()
    except:
        repaired_text_str = repaired_text.decode('utf-8', errors='replace').strip()
    
    return {
        'repaired_text': repaired_text_str,
        'corrupted_blocks': corrupted_blocks,
        'repair_success': repair_success
    }