def decode_qlog_data(encoded_data: str) -> list:
    """
    Decode QLOG (Query Log) data from base64 format and parse log records.
    
    Utility:
        Decodes base64-encoded QLOG data and extracts structured log records
        containing severity levels, subsystem IDs, timestamps, and messages.
    
    Args:
        encoded_data: Base64-encoded string containing QLOG records
    
    Returns:
        List of dictionaries, each containing:
        - severity: Log level (DEBUG, INFO, WARNING, ERROR, FATAL)
        - subsystem: Subsystem ID (integer)
        - timestamp: ISO 8601 formatted timestamp string
        - message: Log message text
    """
    import base64
    import struct
    from datetime import datetime, timezone
    
    # Decode base64 data
    decoded_bytes = base64.b64decode(encoded_data)
    
    # Severity level mapping
    severity_map = {
        0: "FATAL",
        1: "ERROR",
        2: "WARNING",
        3: "INFO",
        4: "DEBUG"
    }
    
    records = []
    offset = 0
    
    while offset < len(decoded_bytes):
        # Read record header (4 bytes: severity + subsystem + timestamp)
        if offset + 4 > len(decoded_bytes):
            break
            
        # First byte: severity (upper 3 bits) and subsystem (lower 5 bits)
        header_byte = decoded_bytes[offset]
        severity_code = (header_byte >> 5) & 0x07
        subsystem = header_byte & 0x1F
        offset += 1
        
        # Next 3 bytes: timestamp (24-bit integer, seconds since epoch)
        if offset + 3 > len(decoded_bytes):
            break
        timestamp_bytes = decoded_bytes[offset:offset+3]
        timestamp_int = int.from_bytes(timestamp_bytes, byteorder='big')
        offset += 3
        
        # Read message length (variable length encoding)
        if offset >= len(decoded_bytes):
            break
        msg_len_byte = decoded_bytes[offset]
        offset += 1
        
        if msg_len_byte & 0x80:  # Multi-byte length
            msg_len = ((msg_len_byte & 0x7F) << 8) | decoded_bytes[offset]
            offset += 1
        else:
            msg_len = msg_len_byte
        
        # Read message
        if offset + msg_len > len(decoded_bytes):
            break
        message = decoded_bytes[offset:offset+msg_len].decode('utf-8', errors='replace')
        offset += msg_len
        
        # Convert timestamp to ISO 8601
        dt = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)
        timestamp_str = dt.isoformat().replace('+00:00', 'Z')
        
        # Create record
        record = {
            "severity": severity_map.get(severity_code, "UNKNOWN"),
            "subsystem": subsystem,
            "timestamp": timestamp_str,
            "message": message
        }
        records.append(record)
    
    return records