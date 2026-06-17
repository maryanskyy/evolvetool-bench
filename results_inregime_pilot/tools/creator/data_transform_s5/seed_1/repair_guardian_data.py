def repair_guardian_data(corrupted_data):
    """
    Repair corrupted GUARDIAN format data using embedded parity information.
    
    Utility:
        Decodes base64-encoded GUARDIAN format data, identifies corrupted blocks
        using parity checks, and attempts to repair them. Returns the repaired text,
        list of corrupted block IDs, and repair success status.
    
    Args:
        corrupted_data (str): Base64-encoded GUARDIAN format data string
    
    Returns:
        dict: Contains keys:
            - 'repaired_text' (str): The recovered/repaired text content
            - 'corrupted_block_ids' (list): IDs of blocks that were corrupted
            - 'repair_success' (bool): True if repair was successful
    """
    import base64
    import struct
    
    try:
        # Decode base64 data
        decoded = base64.b64decode(corrupted_data)
        
        # Parse GUARDIAN format
        # Format: [header][blocks with parity]
        # Each block: [block_id:2][data_length:2][data][parity:1]
        
        blocks = {}
        corrupted_blocks = []
        repaired_text = ""
        
        offset = 0
        while offset < len(decoded):
            if offset + 4 > len(decoded):
                break
            
            # Read block header
            block_id = struct.unpack('>H', decoded[offset:offset+2])[0]
            data_length = struct.unpack('>H', decoded[offset+2:offset+4])[0]
            offset += 4
            
            if offset + data_length + 1 > len(decoded):
                break
            
            # Read block data and parity
            block_data = decoded[offset:offset+data_length]
            parity = decoded[offset+data_length]
            offset += data_length + 1
            
            # Verify parity (XOR of all bytes should equal parity byte)
            calculated_parity = 0
            for byte in block_data:
                calculated_parity ^= byte
            
            is_corrupted = calculated_parity != parity
            
            if is_corrupted:
                corrupted_blocks.append(block_id)
                # Attempt to recover text by XORing with parity
                recovered_data = bytearray(block_data)
                for i in range(len(recovered_data)):
                    recovered_data[i] ^= parity
                try:
                    text = recovered_data.decode('utf-8', errors='ignore')
                    repaired_text += text
                except:
                    pass
            else:
                try:
                    text = block_data.decode('utf-8', errors='ignore')
                    repaired_text += text
                except:
                    pass
            
            blocks[block_id] = {
                'data': block_data,
                'corrupted': is_corrupted,
                'parity': parity
            }
        
        repair_success = len(corrupted_blocks) > 0 or len(blocks) > 0
        
        return {
            'repaired_text': repaired_text.strip(),
            'corrupted_block_ids': corrupted_blocks,
            'repair_success': repair_success
        }
    
    except Exception as e:
        return {
            'repaired_text': '',
            'corrupted_block_ids': [],
            'repair_success': False
        }