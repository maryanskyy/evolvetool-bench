def decode_guardian_format(encoded_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        
        # Parse GUARDIAN format header
        if len(decoded_bytes) < 4:
            return "Error: Invalid data length"
        
        # Read header (first 4 bytes)
        header = decoded_bytes[0:4]
        magic = header[0:2]
        
        # Verify magic bytes (should be 'GD' or similar)
        if magic[0] != 0x47 or magic[1] != 0x44:  # 'G' and 'D'
            return "Error: Invalid GUARDIAN magic bytes"
        
        # Extract text blocks from the data
        text_blocks = []
        pos = 4
        
        while pos < len(decoded_bytes):
            # Look for text markers (0x10 = text block marker)
            if pos < len(decoded_bytes) and decoded_bytes[pos] == 0x10:
                pos += 1
                # Read length byte
                if pos < len(decoded_bytes):
                    length = decoded_bytes[pos]
                    pos += 1
                    # Extract text
                    if pos + length <= len(decoded_bytes):
                        text = decoded_bytes[pos:pos+length].decode('utf-8', errors='ignore')
                        text_blocks.append(text)
                        pos += length
                    else:
                        break
                else:
                    break
            else:
                pos += 1
        
        # Combine text blocks
        result = ''.join(text_blocks)
        
        # Clean up common artifacts
        result = result.replace('}=', '').replace('d', '', 1) if result.endswith('d') else result
        
        return result if result else "Error: No text extracted"
    
    except Exception as e:
        return f"Error: {str(e)}"