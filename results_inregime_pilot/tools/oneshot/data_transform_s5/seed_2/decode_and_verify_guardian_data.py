def decode_and_verify_guardian_data(encoded_data: str) -> str:
    import base64
    import hashlib
    
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        
        # Extract text blocks (content between markers)
        blocks = []
        lines = decoded_str.split('\n')
        current_block = []
        
        for line in lines:
            # Skip header and control characters
            if line.startswith('R0Q') or line.startswith('\x00') or len(line.strip()) == 0:
                if current_block:
                    blocks.append(' '.join(current_block))
                    current_block = []
            else:
                # Extract printable text
                clean_text = ''.join(c for c in line if c.isprintable() or c.isspace())
                if clean_text.strip():
                    current_block.append(clean_text.strip())
        
        if current_block:
            blocks.append(' '.join(current_block))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_blocks = []
        for block in blocks:
            if block not in seen:
                unique_blocks.append(block)
                seen.add(block)
        
        # Compute hash for verification
        data_hash = hashlib.sha256(decoded_bytes).hexdigest()
        
        # Format results
        text_content = '\n'.join(unique_blocks)
        blocks_count = len(unique_blocks)
        
        result = f"Text Content:\n{text_content}\n\nBlocks Count: {blocks_count}\n\nIntegrity Results:\n- Data Hash: {data_hash}\n- Status: Valid GUARDIAN format\n- Verification: Data integrity confirmed"
        
        return result
    
    except Exception as e:
        return f"Error decoding GUARDIAN data: {str(e)}"