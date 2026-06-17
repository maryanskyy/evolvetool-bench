def decode_and_verify_guardian_data(encoded_data):
    """
    Decode and verify GUARDIAN format data with integrity checks.
    
    Utility:
        Decodes base64-encoded GUARDIAN format data blocks and verifies
        their integrity using checksums. Extracts and returns the text
        content along with verification results for each block.
    
    Args:
        encoded_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: Contains 'text' (decoded text content), 'blocks_count' (number
              of blocks found), and 'integrity_results' (list of verification
              results for each block with format, checksum, and validity info)
    """
    import base64
    import struct
    
    try:
        # Decode base64 data
        decoded_bytes = base64.b64decode(encoded_data)
    except Exception as e:
        return {
            'text': '',
            'blocks_count': 0,
            'integrity_results': [f'Base64 decode error: {str(e)}'],
            'error': str(e)
        }
    
    blocks = []
    integrity_results = []
    text_content = []
    offset = 0
    
    # Parse GUARDIAN blocks
    while offset < len(decoded_bytes):
        if offset + 4 > len(decoded_bytes):
            break
        
        # Read block header (4 bytes: magic + flags)
        magic = decoded_bytes[offset]
        flags = decoded_bytes[offset + 1]
        block_size = struct.unpack('>H', decoded_bytes[offset + 2:offset + 4])[0]
        
        if magic != 0x47:  # 'G' in ASCII
            break
        
        offset += 4
        
        if offset + block_size > len(decoded_bytes):
            break
        
        block_data = decoded_bytes[offset:offset + block_size]
        offset += block_size
        
        # Parse block content
        if len(block_data) >= 2:
            content_type = block_data[0]
            content_length = block_data[1]
            
            if len(block_data) >= 2 + content_length:
                content = block_data[2:2 + content_length]
                
                # Extract checksum if present
                checksum_offset = 2 + content_length
                checksum = None
                if checksum_offset + 2 <= len(block_data):
                    checksum = struct.unpack('>H', block_data[checksum_offset:checksum_offset + 2])[0]
                
                # Verify integrity
                calculated_checksum = sum(content) & 0xFFFF
                is_valid = (checksum is None) or (checksum == calculated_checksum)
                
                try:
                    text = content.decode('utf-8', errors='replace')
                    text_content.append(text)
                except:
                    text = ''
                
                blocks.append({
                    'type': content_type,
                    'content': text,
                    'checksum': checksum,
                    'calculated_checksum': calculated_checksum
                })
                
                integrity_results.append({
                    'block_index': len(blocks) - 1,
                    'format': 'GUARDIAN',
                    'checksum_provided': checksum,
                    'checksum_calculated': calculated_checksum,
                    'valid': is_valid,
                    'content_preview': text[:50] + ('...' if len(text) > 50 else '')
                })
    
    return {
        'text': ''.join(text_content),
        'blocks_count': len(blocks),
        'integrity_results': integrity_results,
        'blocks': blocks
    }