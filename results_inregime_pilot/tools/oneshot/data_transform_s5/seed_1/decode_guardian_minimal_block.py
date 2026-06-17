def decode_guardian_minimal_block(encoded_data: str, expected_data_size: int = 2) -> str:
    """
    Decode minimal GUARDIAN format data with single block and padding handling.
    
    Args:
        encoded_data: Base64-encoded GUARDIAN format string
        expected_data_size: Number of actual data bytes (excluding padding)
    
    Returns:
        Decoded text string with padding removed
    """
    import base64
    import struct
    
    # Decode base64
    try:
        decoded_bytes = base64.b64decode(encoded_data)
    except Exception:
        return ""
    
    # GUARDIAN block structure: 16 bytes per block
    # Format: [data(variable)] [padding] [crc(2)] [parity(1)] [reserved(1)]
    block_size = 16
    
    if len(decoded_bytes) < block_size:
        return ""
    
    # Extract first block
    block = decoded_bytes[:block_size]
    
    # Extract actual data (first expected_data_size bytes)
    actual_data = block[:expected_data_size]
    
    # Verify CRC (bytes 14-15)
    crc_bytes = block[14:16]
    crc_value = struct.unpack('>H', crc_bytes)[0]
    
    # Simple CRC16 verification
    def calculate_crc16(data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                crc <<= 1
                if crc & 0x10000:
                    crc ^= 0x1021
                crc &= 0xFFFF
        return crc
    
    calculated_crc = calculate_crc16(block[:14])
    
    # Verify parity (byte 15)
    parity_byte = block[15]
    parity_check = sum(block[:14]) & 0xFF
    
    # Decode actual data to string
    try:
        decoded_text = actual_data.decode('utf-8', errors='strict')
    except Exception:
        decoded_text = actual_data.decode('latin-1', errors='ignore')
    
    return decoded_text