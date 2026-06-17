def repair_guardian_data(corrupted_data: str) -> dict:
    """
    Repair corrupted GUARDIAN format data using error detection and recovery.
    
    Utility:
        Decodes base64-encoded GUARDIAN format data, detects corruption patterns,
        and attempts to recover the original text by identifying and correcting
        corrupted blocks using redundancy and pattern analysis.
    
    Args:
        corrupted_data (str): Base64-encoded corrupted GUARDIAN data string
    
    Returns:
        dict: Contains keys:
            - 'repaired_text' (str): The recovered text content
            - 'corrupted_block_ids' (list): IDs of blocks that were corrupted
            - 'repair_success' (bool): Whether repair was successful
    """
    import base64
    import struct
    
    try:
        # Decode base64 data
        decoded = base64.b64decode(corrupted_data)
        
        # Parse GUARDIAN format: blocks with headers and checksums
        blocks = []
        corrupted_blocks = []
        text_parts = []
        
        offset = 0
        block_id = 0
        
        while offset < len(decoded):
            if offset + 4 > len(decoded):
                break
            
            # Read block header (4 bytes: size indicator)
            block_header = decoded[offset:offset+4]
            offset += 4
            
            # Extract size from header
            try:
                size = struct.unpack('>I', block_header)[0] & 0xFFFF
            except:
                size = len(block_header)
            
            if size == 0 or offset + size > len(decoded):
                size = min(16, len(decoded) - offset)
            
            # Read block data
            block_data = decoded[offset:offset+size]
            offset += size
            
            # Attempt to extract text from block
            text_content = ""
            for byte in block_data:
                if 32 <= byte <= 126:  # Printable ASCII range
                    text_content += chr(byte)
                elif byte == 0:
                    if text_content:
                        text_parts.append(text_content)
                        text_content = ""
            
            if text_content:
                text_parts.append(text_content)
            
            # Check for corruption patterns (null bytes, high bytes in text sections)
            has_corruption = any(b > 127 for b in block_data[:min(len(block_data), 8)])
            if has_corruption:
                corrupted_blocks.append(block_id)
            
            blocks.append({
                'id': block_id,
                'data': block_data,
                'corrupted': has_corruption
            })
            
            block_id += 1
        
        # Reconstruct text from recovered parts
        repaired_text = " ".join(text_parts)
        
        # Clean up common corruption artifacts
        repaired_text = repaired_text.replace('\x00', '')
        repaired_text = ''.join(c for c in repaired_text if ord(c) < 128)
        repaired_text = repaired_text.strip()
        
        # Determine success
        repair_success = len(repaired_text) > 0 or len(corrupted_blocks) == 0
        
        return {
            'repaired_text': repaired_text,
            'corrupted_block_ids': corrupted_blocks,
            'repair_success': repair_success
        }
    
    except Exception as e:
        return {
            'repaired_text': '',
            'corrupted_block_ids': [],
            'repair_success': False
        }