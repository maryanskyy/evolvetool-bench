def repair_guardian_data_with_redundancy(corrupted_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64
        decoded = base64.b64decode(corrupted_data)
        
        # Parse GUARDIAN format: blocks with headers and checksums
        blocks = []
        pos = 0
        block_id = 0
        corrupted_blocks = []
        
        while pos < len(decoded):
            if pos + 4 > len(decoded):
                break
            
            # Read block header (4 bytes: size)
            block_size = struct.unpack('>I', decoded[pos:pos+4])[0]
            pos += 4
            
            if block_size == 0 or pos + block_size > len(decoded):
                corrupted_blocks.append(block_id)
                block_id += 1
                continue
            
            # Extract block data
            block_data = decoded[pos:pos+block_size]
            pos += block_size
            
            # Validate block (check for null bytes and printable content)
            if len(block_data) > 0 and not all(b == 0 for b in block_data):
                blocks.append((block_id, block_data))
            else:
                corrupted_blocks.append(block_id)
            
            block_id += 1
        
        # Reconstruct text from valid blocks
        reconstructed_text = ""
        for bid, bdata in blocks:
            try:
                # Attempt to decode as UTF-8, skip null bytes
                text_part = bdata.decode('utf-8', errors='ignore').replace('\x00', '')
                reconstructed_text += text_part
            except:
                pass
        
        # Clean up the reconstructed text
        reconstructed_text = reconstructed_text.strip()
        
        # Determine success: if we recovered substantial text and have valid blocks
        success = len(reconstructed_text) > 20 and len(blocks) >= 2
        
        # Format result
        result = f"Repaired Text: {reconstructed_text}\n"
        result += f"Corrupted Block IDs: {corrupted_blocks}\n"
        result += f"Repair Success Status: {'✓ SUCCESS' if success else '✗ FAILED'}"
        
        return result
    
    except Exception as e:
        return f"Repair Error: {str(e)}\nCorrupted Block IDs: []\nRepair Success Status: ✗ FAILED"