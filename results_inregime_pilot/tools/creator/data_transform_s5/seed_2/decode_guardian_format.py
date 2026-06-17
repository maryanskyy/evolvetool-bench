def decode_guardian_format(data_b64):
    """
    Decode and verify GUARDIAN (Guarded Data Integrity Archive) format data.
    
    Utility:
        Decodes Base64-encoded GUARDIAN format blocks, verifies CRC-16/CCITT checksums,
        validates XOR parity, and extracts the original text data.
    
    Args:
        data_b64 (str): Base64-encoded GUARDIAN format data
    
    Returns:
        dict: Contains 'text' (decoded UTF-8), 'blocks' (total data blocks),
              and 'integrity' (list of dicts with block_id, crc_valid, parity_valid)
    """
    import base64
    import struct
    
    # Decode Base64
    data = base64.b64decode(data_b64)
    
    # Parse header
    magic = data[0:2]
    version = data[2]
    block_size = data[3]
    parity_group_size = data[4]
    total_data_blocks = data[5]
    
    # CRC-16/CCITT calculation
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
    blocks_data = {}
    integrity = []
    text_parts = []
    
    for i in range(total_data_blocks):
        block_id = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        
        data_length = data[offset]
        offset += 1
        
        block_data = data[offset:offset+block_size]
        offset += block_size
        
        crc_stored = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        
        xor_parity_stored = data[offset]
        offset += 1
        
        # Verify CRC on unpadded data
        unpadded_data = block_data[:data_length]
        crc_calculated = crc16_ccitt(unpadded_data)
        crc_valid = (crc_calculated == crc_stored)
        
        # Verify XOR parity on unpadded data
        xor_parity_calculated = 0
        for byte in unpadded_data:
            xor_parity_calculated ^= byte
        parity_valid = (xor_parity_calculated == xor_parity_stored)
        
        blocks_data[block_id] = {
            'data': unpadded_data,
            'padded_data': block_data,
            'crc_valid': crc_valid,
            'parity_valid': parity_valid
        }
        
        integrity.append({
            'block_id': block_id,
            'crc_valid': crc_valid,
            'parity_valid': parity_valid
        })
        
        # Collect text
        text_parts.append(unpadded_data.decode('utf-8', errors='ignore'))
    
    # Combine text from all blocks
    text = ''.join(text_parts)
    
    return {
        'text': text,
        'blocks': total_data_blocks,
        'integrity': integrity
    }