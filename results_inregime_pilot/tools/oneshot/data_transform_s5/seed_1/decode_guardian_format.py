def decode_guardian_format(data_b64: str) -> str:
    import base64
    import struct
    import json
    
    # Decode Base64
    data = base64.b64decode(data_b64)
    
    # Parse header
    magic = data[0:2]
    version = data[2]
    block_size = data[3]
    parity_group_size = data[4]
    total_data_blocks = data[5]
    
    # Verify magic
    if magic != b'GD':
        return json.dumps({'error': 'Invalid magic number'})
    
    # CRC-16/CCITT implementation
    def crc16_ccitt(data_bytes):
        crc = 0xFFFF
        poly = 0x1021
        for byte in data_bytes:
            crc ^= (byte << 8)
            for _ in range(8):
                crc <<= 1
                if crc & 0x10000:
                    crc ^= poly
                crc &= 0xFFFF
        return crc
    
    # Parse data blocks
    offset = 6
    blocks = []
    block_data = {}
    parity_groups = {}
    
    for i in range(total_data_blocks):
        block_id = struct.unpack('>H', data[offset:offset+2])[0]
        data_length = data[offset+2]
        block_payload = data[offset+3:offset+3+block_size]
        unpadded_data = block_payload[:data_length]
        crc_stored = struct.unpack('>H', data[offset+3+block_size:offset+5+block_size])[0]
        xor_parity = data[offset+5+block_size]
        
        # Verify CRC
        crc_computed = crc16_ccitt(unpadded_data)
        crc_valid = (crc_computed == crc_stored)
        
        # Verify XOR parity
        xor_computed = 0
        for byte in unpadded_data:
            xor_computed ^= byte
        parity_valid = (xor_computed == xor_parity)
        
        blocks.append({
            'block_id': block_id,
            'crc_valid': crc_valid,
            'parity_valid': parity_valid
        })
        
        block_data[block_id] = unpadded_data
        
        # Track parity groups
        group = block_id % parity_group_size
        if group not in parity_groups:
            parity_groups[group] = []
        parity_groups[group].append(block_payload)
        
        offset += 7 + block_size
    
    # Decode text from blocks
    text = b''
    for i in range(total_data_blocks):
        if i in block_data:
            text += block_data[i]
    
    try:
        text_str = text.decode('utf-8')
    except:
        text_str = text.hex()
    
    result = {
        'text': text_str,
        'blocks': total_data_blocks,
        'integrity': blocks
    }
    
    return json.dumps(result)