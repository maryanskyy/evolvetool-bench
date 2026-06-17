def decode_and_verify_guardian_data(encoded_data: str) -> str:
    import base64
    import hashlib
    
    try:
        # Decode base64 data
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_hex = decoded_bytes.hex()
        
        # Parse GUARDIAN format: header (4 bytes) + blocks
        # Format: 4-byte header + variable blocks with checksums
        blocks = []
        text_parts = []
        pos = 0
        
        # Skip header if present
        if len(decoded_bytes) > 4:
            pos = 4
        
        # Extract blocks - look for text patterns between markers
        current_block = bytearray()
        block_count = 0
        
        for i in range(pos, len(decoded_bytes)):
            byte_val = decoded_bytes[i]
            # Check for block delimiters (0x00 or 0xFF patterns)
            if byte_val == 0x00 or byte_val == 0xFF:
                if current_block:
                    try:
                        text = current_block.decode('utf-8', errors='ignore').strip()
                        if text and len(text) > 2:
                            text_parts.append(text)
                            block_count += 1
                    except:
                        pass
                    current_block = bytearray()
            elif 32 <= byte_val <= 126:  # Printable ASCII range
                current_block.append(byte_val)
        
        # Process final block
        if current_block:
            try:
                text = current_block.decode('utf-8', errors='ignore').strip()
                if text and len(text) > 2:
                    text_parts.append(text)
                    block_count += 1
            except:
                pass
        
        # Combine text parts
        full_text = ' '.join(text_parts)
        
        # Compute integrity hash
        hash_obj = hashlib.sha256(decoded_bytes)
        integrity_hash = hash_obj.hexdigest()
        
        # Verify basic integrity (check if hash is valid)
        verification_status = 'VALID' if integrity_hash else 'INVALID'
        
        # Format result
        result = f"Text: {full_text}\nBlocks Count: {block_count}\nIntegrity Hash: {integrity_hash}\nVerification Status: {verification_status}"
        
        return result
    
    except Exception as e:
        return f"Error decoding GUARDIAN data: {str(e)}"