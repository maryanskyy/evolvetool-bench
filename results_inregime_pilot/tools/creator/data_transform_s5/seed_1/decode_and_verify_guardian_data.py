def decode_and_verify_guardian_data(encoded_data):
    """
    Decode and verify GUARDIAN format data with integrity checks.
    
    Utility:
        Decodes GUARDIAN encoded data blocks and verifies their integrity
        using checksums. Returns decoded text and verification results.
    
    Args:
        encoded_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: Contains 'text' (decoded string), 'blocks' (count), 
              'integrity_results' (list of verification results),
              'status' (success/failure indicator)
    """
    import base64
    import struct
    
    result = {
        'text': '',
        'blocks': 0,
        'integrity_results': [],
        'status': 'failed'
    }
    
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        
        if len(decoded_bytes) < 4:
            result['integrity_results'].append('Data too short')
            return result
        
        # Parse header
        offset = 0
        header = decoded_bytes[offset:offset+4]
        offset += 4
        
        # Check for GUARDIAN signature (0x47 0x44 = 'GD')
        if header[0:2] != b'GD':
            result['integrity_results'].append('Invalid GUARDIAN signature')
            return result
        
        block_count = struct.unpack('>H', header[2:4])[0]
        result['blocks'] = block_count
        
        decoded_text_parts = []
        
        # Parse blocks
        for block_idx in range(block_count):
            if offset + 6 > len(decoded_bytes):
                result['integrity_results'].append(f'Block {block_idx}: Incomplete header')
                continue
            
            # Block header: type (1), flags (1), length (2), checksum (2)
            block_type = decoded_bytes[offset]
            flags = decoded_bytes[offset + 1]
            block_length = struct.unpack('>H', decoded_bytes[offset+2:offset+4])[0]
            stored_checksum = struct.unpack('>H', decoded_bytes[offset+4:offset+6])[0]
            offset += 6
            
            if offset + block_length > len(decoded_bytes):
                result['integrity_results'].append(f'Block {block_idx}: Incomplete data')
                continue
            
            block_data = decoded_bytes[offset:offset+block_length]
            offset += block_length
            
            # Calculate checksum
            calculated_checksum = sum(block_data) & 0xFFFF
            
            # Verify integrity
            if calculated_checksum == stored_checksum:
                result['integrity_results'].append(
                    f'Block {block_idx}: VALID (checksum: {stored_checksum:04x})'
                )
                # Decode text block
                if block_type == 0x01:
                    try:
                        text = block_data.decode('utf-8')
                        decoded_text_parts.append(text)
                    except UnicodeDecodeError:
                        result['integrity_results'].append(
                            f'Block {block_idx}: Failed to decode as UTF-8'
                        )
            else:
                result['integrity_results'].append(
                    f'Block {block_idx}: INVALID (expected: {stored_checksum:04x}, got: {calculated_checksum:04x})'
                )
        
        result['text'] = ''.join(decoded_text_parts)
        result['status'] = 'success' if result['blocks'] > 0 else 'no_blocks'
        
    except Exception as e:
        result['integrity_results'].append(f'Error: {str(e)}')
        result['status'] = 'error'
    
    return result