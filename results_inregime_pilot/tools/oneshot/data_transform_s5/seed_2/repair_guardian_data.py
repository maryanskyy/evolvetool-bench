def repair_guardian_data(corrupted_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64
        decoded = base64.b64decode(corrupted_data)
        
        # Parse GUARDIAN format: header (4 bytes) + blocks
        if len(decoded) < 4:
            return 'ERROR: Invalid data length'
        
        # Extract blocks and repair
        repaired_text = ''
        corrupted_blocks = []
        block_id = 0
        offset = 0
        
        while offset < len(decoded):
            # Read block header (2 bytes: size)
            if offset + 2 > len(decoded):
                break
            
            block_size = struct.unpack('>H', decoded[offset:offset+2])[0]
            offset += 2
            
            if offset + block_size > len(decoded):
                block_size = len(decoded) - offset
            
            # Extract block data
            block_data = decoded[offset:offset+block_size]
            offset += block_size
            
            # Detect and repair corruption (remove non-printable chars, fix common corruptions)
            repaired_block = ''
            is_corrupted = False
            
            for byte in block_data:
                if 32 <= byte <= 126:  # Printable ASCII
                    repaired_block += chr(byte)
                elif byte in [9, 10, 13]:  # Tab, newline, carriage return
                    repaired_block += chr(byte)
                else:
                    is_corrupted = True
                    # Skip corrupted byte or replace with space
                    if byte > 0:
                        repaired_block += ' '
            
            if is_corrupted:
                corrupted_blocks.append(block_id)
            
            repaired_text += repaired_block
            block_id += 1
        
        # Clean up extra spaces and return formatted result
        repaired_text = ' '.join(repaired_text.split())
        
        result = f'Repaired Text: {repaired_text}\n'
        result += f'Corrupted Block IDs: {corrupted_blocks if corrupted_blocks else "None"}\n'
        result += f'Repair Success: {"SUCCESSFUL" if repaired_text else "FAILED"}'
        
        return result
    
    except Exception as e:
        return f'ERROR: {str(e)}'