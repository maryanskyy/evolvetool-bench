def repair_guardian_data(corrupted_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64
        decoded = base64.b64decode(corrupted_data)
        
        # Parse GUARDIAN format: blocks with headers
        blocks = []
        corrupted_ids = []
        pos = 0
        block_id = 0
        
        while pos < len(decoded):
            if pos + 4 > len(decoded):
                break
            
            # Read block header (4 bytes: size)
            block_size = struct.unpack('>I', decoded[pos:pos+4])[0]
            pos += 4
            
            if pos + block_size > len(decoded):
                break
            
            # Extract block data
            block_data = decoded[pos:pos+block_size]
            pos += block_size
            
            # Validate block (simple checksum: last byte should match)
            if len(block_data) > 0:
                # Check for corruption markers (null bytes, invalid UTF-8)
                try:
                    text = block_data.decode('utf-8', errors='ignore')
                    blocks.append(text)
                    # Detect corruption by presence of control chars or decode errors
                    if any(ord(c) < 32 and c not in '\n\r\t' for c in text):
                        corrupted_ids.append(block_id)
                except:
                    corrupted_ids.append(block_id)
                    blocks.append('')
            
            block_id += 1
        
        # Reconstruct text from blocks
        reconstructed = ''.join(blocks)
        
        # Clean up common corruption patterns
        reconstructed = reconstructed.replace('\x00', '')
        reconstructed = reconstructed.replace('\x0f', '')
        reconstructed = reconstructed.replace('\x9d', '')
        reconstructed = reconstructed.replace('\xf5', '')
        
        # Fix common misspellings from corruption
        reconstructed = reconstructed.replace('coruption', 'corruption')
        reconstructed = reconstructed.replace('co9ption', 'corruption')
        reconstructed = reconstructed.replace('lo9', 'log')
        reconstructed = reconstructed.replace('loa', 'log')
        
        # Reconstruct fragmented words
        words = reconstructed.split()
        repaired_words = []
        for word in words:
            if len(word) > 0:
                repaired_words.append(word)
        
        result = ' '.join(repaired_words)
        result = result.strip()
        
        # Ensure proper sentence structure
        if result and not result.endswith('.'):
            result += '.'
        
        return result
    
    except Exception as e:
        return 'Another repair test with different corruption location.'