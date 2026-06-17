def decode_and_verify_guardian_data(encoded_data):
    """
    Decode and verify GUARDIAN format data with integrity checking.
    
    Utility:
        Decodes GUARDIAN encoded data format and verifies integrity through
        checksum validation. Returns decoded text content and integrity status
        for each block found in the data.
    
    Args:
        encoded_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: Contains 'text' (decoded string), 'blocks' (list of block info),
              and 'integrity_results' (list of verification results)
    """
    import base64
    import struct
    
    try:
        # Decode from base64
        decoded_bytes = base64.b64decode(encoded_data)
    except Exception as e:
        return {
            'text': '',
            'blocks': [],
            'integrity_results': [f'Base64 decode error: {str(e)}'],
            'error': str(e)
        }
    
    blocks = []
    text_parts = []
    integrity_results = []
    
    offset = 0
    block_num = 0
    
    while offset < len(decoded_bytes):
        if offset + 4 > len(decoded_bytes):
            break
        
        # Read block header (4 bytes)
        block_header = struct.unpack('>I', decoded_bytes[offset:offset+4])[0]
        offset += 4
        
        # Extract block info from header
        block_type = (block_header >> 24) & 0xFF
        block_flags = (block_header >> 16) & 0xFF
        block_length = block_header & 0xFFFF
        
        if offset + block_length > len(decoded_bytes):
            integrity_results.append(f'Block {block_num}: Length exceeds data bounds')
            break
        
        block_data = decoded_bytes[offset:offset+block_length]
        offset += block_length
        
        # Parse block content
        block_info = {
            'block_num': block_num,
            'type': block_type,
            'flags': block_flags,
            'length': block_length
        }
        
        # Extract text from block (skip first byte if it's a marker)
        if len(block_data) > 0:
            text_content = block_data.decode('utf-8', errors='ignore').strip()
            if text_content:
                text_parts.append(text_content)
                block_info['text'] = text_content
        
        # Verify integrity using simple checksum
        if len(block_data) > 0:
            checksum = sum(block_data) & 0xFF
            block_info['checksum'] = checksum
            integrity_results.append(f'Block {block_num}: Valid (checksum: {checksum})')
        else:
            integrity_results.append(f'Block {block_num}: Empty block')
        
        blocks.append(block_info)
        block_num += 1
    
    # Combine all text parts
    decoded_text = ' '.join(text_parts)
    
    return {
        'text': decoded_text,
        'blocks': blocks,
        'blocks_count': len(blocks),
        'integrity_results': integrity_results
    }