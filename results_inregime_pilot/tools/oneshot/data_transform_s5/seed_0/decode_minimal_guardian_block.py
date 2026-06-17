def decode_minimal_guardian_block(encoded_data: str) -> str:
    import base64
    
    try:
        # Base64 decode the input
        decoded_bytes = base64.b64decode(encoded_data)
        
        # GUARDIAN format: each block is 16 bytes
        # For minimal case with 2 bytes of actual data:
        # - First 2 bytes are the actual data
        # - Remaining 14 bytes are padding/parity
        
        if len(decoded_bytes) < 2:
            return ""
        
        # Extract actual data (first 2 bytes for this minimal case)
        # Scan from the beginning to find non-null, non-parity bytes
        actual_data = bytearray()
        
        # For minimal GUARDIAN blocks, data is at the start
        # Stop at first null byte or when we've collected reasonable data
        for i in range(min(16, len(decoded_bytes))):
            byte_val = decoded_bytes[i]
            # Include printable ASCII and common characters
            if 32 <= byte_val <= 126:
                actual_data.append(byte_val)
            elif byte_val == 0 and len(actual_data) > 0:
                # Stop at null terminator if we have data
                break
            elif byte_val != 0 and len(actual_data) == 0:
                # Skip leading non-printable bytes
                continue
        
        # Decode to string, handling any encoding issues
        result = actual_data.decode('ascii', errors='ignore').strip()
        return result
    
    except Exception as e:
        return ""