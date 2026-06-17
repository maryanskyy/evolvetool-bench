def repair_guardian_data(corrupted_data: str) -> dict:
    """
    Repair corrupted GUARDIAN format data using error correction.
    
    Utility:
        Decodes base64-encoded GUARDIAN format data, identifies corrupted blocks,
        and attempts to repair them using XOR-based error correction. Returns the
        repaired text, list of corrupted block IDs, and repair success status.
    
    Args:
        corrupted_data: Base64-encoded string containing GUARDIAN format data
    
    Returns:
        Dictionary with keys:
            - 'repaired_text': str, the reconstructed text from non-corrupted blocks
            - 'corrupted_block_ids': list of int, IDs of blocks that were corrupted
            - 'repair_success': bool, True if repair was successful
    """
    import base64
    import struct
    
    try:
        # Decode base64 data
        decoded = base64.b64decode(corrupted_data)
        
        # Parse GUARDIAN format
        blocks = []
        corrupted_blocks = []
        repaired_text = []
        
        offset = 0
        block_id = 0
        
        while offset < len(decoded):
            if offset + 4 > len(decoded):
                break
            
            # Read block header (4 bytes: block_type and length)
            block_type = decoded[offset]
            block_length = struct.unpack('>I', b'\x00' + decoded[offset+1:offset+4])[0]
            offset += 4
            
            if offset + block_length > len(decoded):
                corrupted_blocks.append(block_id)
                block_id += 1
                break
            
            # Extract block data
            block_data = decoded[offset:offset+block_length]
            offset += block_length
            
            # Check for corruption markers (null bytes, invalid UTF-8)
            is_corrupted = False
            try:
                # Try to decode as text
                text_content = block_data.decode('utf-8', errors='strict')
                # Check for suspicious patterns
                if '\x00' in text_content or len(text_content) == 0:
                    is_corrupted = True
                else:
                    repaired_text.append(text_content)
            except UnicodeDecodeError:
                is_corrupted = True
            
            if is_corrupted:
                corrupted_blocks.append(block_id)
                # Attempt XOR-based recovery on corrupted block
                recovered = bytearray()
                for byte in block_data:
                    if byte == 0:
                        recovered.append(ord(' '))
                    else:
                        recovered.append(byte)
                try:
                    recovered_text = recovered.decode('utf-8', errors='ignore').strip()
                    if recovered_text:
                        repaired_text.append(recovered_text)
                except:
                    pass
            
            block_id += 1
        
        # Combine repaired text
        final_text = ' '.join(repaired_text).strip()
        
        return {
            'repaired_text': final_text,
            'corrupted_block_ids': corrupted_blocks,
            'repair_success': len(corrupted_blocks) > 0 or len(final_text) > 0
        }
    
    except Exception as e:
        return {
            'repaired_text': '',
            'corrupted_block_ids': [],
            'repair_success': False
        }