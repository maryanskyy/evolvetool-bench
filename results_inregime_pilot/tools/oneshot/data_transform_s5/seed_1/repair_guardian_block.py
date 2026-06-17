def repair_guardian_block(encoded_data, parity_group_size=4):
    import base64
    import struct
    import zlib
    
    try:
        decoded = base64.b64decode(encoded_data)
    except Exception:
        return '{"repaired_text": "", "corrupted_blocks": [], "repair_success": false}'
    
    blocks = {}
    corrupted_blocks = []
    block_data = {}
    block_crc = {}
    parity_blocks = {}
    
    offset = 0
    while offset < len(decoded):
        if offset + 6 > len(decoded):
            break
        
        block_id = struct.unpack('>H', decoded[offset:offset+2])[0]
        block_len = struct.unpack('>H', decoded[offset+2:offset+4])[0]
        crc_stored = struct.unpack('>H', decoded[offset+4:offset+6])[0]
        
        if offset + 6 + block_len > len(decoded):
            break
        
        block_content = decoded[offset+6:offset+6+block_len]
        crc_calc = zlib.crc32(block_content) & 0xFFFF
        
        block_data[block_id] = block_content
        block_crc[block_id] = crc_calc
        
        if crc_calc != crc_stored:
            corrupted_blocks.append(block_id)
        
        offset += 6 + block_len
    
    repaired_blocks = {}
    for corrupted_id in corrupted_blocks:
        parity_group = corrupted_id % parity_group_size
        group_members = [bid for bid in block_data.keys() if bid % parity_group_size == parity_group]
        
        if len(group_members) < 2:
            continue
        
        parity_id = max(group_members)
        if parity_id not in block_data:
            continue
        
        repaired = bytearray(block_data[parity_id])
        
        for member_id in group_members:
            if member_id != parity_id and member_id != corrupted_id:
                if member_id in block_data:
                    member_data = block_data[member_id]
                    for i in range(min(len(repaired), len(member_data))):
                        repaired[i] ^= member_data[i]
        
        repaired_blocks[corrupted_id] = bytes(repaired)
    
    repaired_text = ""
    for block_id in sorted(block_data.keys()):
        if block_id in repaired_blocks:
            try:
                repaired_text += repaired_blocks[block_id].decode('utf-8', errors='ignore')
            except Exception:
                pass
        else:
            try:
                repaired_text += block_data[block_id].decode('utf-8', errors='ignore')
            except Exception:
                pass
    
    repair_success = len(corrupted_blocks) > 0 and len(repaired_blocks) == len(corrupted_blocks)
    
    result = '{"repaired_text": "' + repaired_text.replace('"', '\\"') + '", "corrupted_blocks": ' + str(corrupted_blocks) + ', "repair_success": ' + ('true' if repair_success else 'false') + '}'
    return result