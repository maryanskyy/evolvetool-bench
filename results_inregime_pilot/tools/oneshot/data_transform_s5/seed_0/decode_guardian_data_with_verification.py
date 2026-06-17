def decode_guardian_data_with_verification(encoded_data: str) -> str:
    import base64
    import hashlib
    
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        
        # Parse GUARDIAN format
        blocks = []
        text_parts = []
        pos = 0
        block_count = 0
        
        while pos < len(decoded_bytes):
            # Read block header (4 bytes: magic + flags)
            if pos + 4 > len(decoded_bytes):
                break
            
            magic = decoded_bytes[pos]
            flags = decoded_bytes[pos + 1]
            block_len = int.from_bytes(decoded_bytes[pos + 2:pos + 4], 'big')
            pos += 4
            
            # Read block data
            if pos + block_len > len(decoded_bytes):
                break
            
            block_data = decoded_bytes[pos:pos + block_len]
            pos += block_len
            
            # Read checksum (4 bytes)
            if pos + 4 > len(decoded_bytes):
                break
            
            stored_checksum = int.from_bytes(decoded_bytes[pos:pos + 4], 'big')
            pos += 4
            
            # Verify checksum
            computed_checksum = int.from_bytes(hashlib.sha256(block_data).digest()[:4], 'big')
            is_valid = stored_checksum == computed_checksum
            
            # Extract text (skip first byte which is often a marker)
            if len(block_data) > 1:
                text = block_data[1:].decode('utf-8', errors='ignore')
                text_parts.append(text)
            
            blocks.append({'valid': is_valid, 'data': block_data})
            block_count += 1
        
        # Compute overall integrity hash
        all_data = b''.join([b['data'] for b in blocks])
        integrity_hash = hashlib.sha256(all_data).hexdigest()
        
        # Determine verification status
        all_valid = all(b['valid'] for b in blocks)
        status = '✓ VALID' if all_valid else '✗ INVALID'
        
        # Format result
        decoded_text = ''.join(text_parts)
        result = f"Decoded Text: {decoded_text}\n"
        result += f"Blocks Count: {block_count}\n"
        result += f"Verification Status: {status}\n"
        result += f"Integrity Hash: {integrity_hash}"
        
        return result
    
    except Exception as e:
        return f"Error decoding GUARDIAN data: {str(e)}"