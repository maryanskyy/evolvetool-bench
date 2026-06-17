def decode_qlog_binary(base64_data):
    """
    Decode QLOG (Quantized Log Format) binary data into structured log records.
    
    Utility:
        Parses base64-encoded QLOG binary format into human-readable log records
        with timestamp, severity level, subsystem ID, and message text.
    
    Args:
        base64_data (str): Base64-encoded QLOG binary data string
    
    Returns:
        list: List of dicts with keys: severity (str), subsystem (int), 
              timestamp (ISO format str), message (str)
    """
    import base64
    from datetime import datetime, timedelta
    
    # Decode base64 data
    binary_data = base64.b64decode(base64_data)
    
    # Reference epoch: 2025-01-01 00:00:00 UTC
    epoch = datetime(2025, 1, 1, 0, 0, 0)
    
    # Severity level mapping
    severity_map = {
        0: "TRACE",
        1: "DEBUG",
        2: "INFO",
        3: "WARN",
        4: "ERROR",
        5: "FATAL"
    }
    
    records = []
    i = 0
    
    while i < len(binary_data):
        # Check for entry separator (0xFE 0xFE)
        if i + 1 < len(binary_data) and binary_data[i] == 0xFE and binary_data[i + 1] == 0xFE:
            i += 2
            continue
        
        # Need at least 8 bytes for header
        if i + 8 > len(binary_data):
            break
        
        # Parse header
        # Bytes 0-3: uint32 big-endian timestamp
        timestamp_seconds = int.from_bytes(binary_data[i:i+4], byteorder='big')
        
        # Byte 4: packed severity and subsystem
        severity_byte = binary_data[i + 4]
        severity_level = (severity_byte >> 4) & 0x0F
        subsystem_id = severity_byte & 0x0F
        
        # Byte 5: flags
        flags = binary_data[i + 5]
        
        # Bytes 6-7: uint16 big-endian payload length
        payload_length = int.from_bytes(binary_data[i+6:i+8], byteorder='big')
        
        # Extract payload
        payload_start = i + 8
        payload_end = payload_start + payload_length
        
        if payload_end > len(binary_data):
            break
        
        message = binary_data[payload_start:payload_end].decode('utf-8', errors='replace')
        
        # Convert timestamp to ISO format
        timestamp_dt = epoch + timedelta(seconds=timestamp_seconds)
        timestamp_iso = timestamp_dt.isoformat() + 'Z'
        
        # Create record
        record = {
            "severity": severity_map.get(severity_level, "UNKNOWN"),
            "subsystem": subsystem_id,
            "timestamp": timestamp_iso,
            "message": message
        }
        records.append(record)
        
        # Move to next entry
        i = payload_end
    
    return records