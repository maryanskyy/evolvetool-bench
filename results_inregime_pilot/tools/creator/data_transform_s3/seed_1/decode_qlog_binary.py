def decode_qlog_binary(base64_data):
    """
    Decode QLOG (Quantized Log Format) binary data into structured log records.
    
    Utility:
        Parses base64-encoded QLOG binary data and extracts log entries with
        timestamps, severity levels, subsystem IDs, and message text.
    
    Args:
        base64_data (str): Base64-encoded QLOG binary data string
    
    Returns:
        list: List of dicts with keys:
            - severity (str): Severity level name (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
            - subsystem (int): Subsystem ID (0-15)
            - timestamp (str): ISO 8601 formatted timestamp
            - message (str): UTF-8 decoded message text
    """
    import base64
    from datetime import datetime, timedelta
    
    # Decode base64 data
    binary_data = base64.b64decode(base64_data)
    
    # Severity level mapping
    severity_map = {
        0: "TRACE",
        1: "DEBUG",
        2: "INFO",
        3: "WARN",
        4: "ERROR",
        5: "FATAL"
    }
    
    # Base timestamp: 2025-01-01 00:00:00 UTC
    base_timestamp = datetime(2025, 1, 1, 0, 0, 0)
    
    # Split by entry separator (0xFE 0xFE)
    separator = b'\xfe\xfe'
    entries_raw = binary_data.split(separator)
    
    log_records = []
    
    for entry_data in entries_raw:
        if len(entry_data) < 8:
            continue
        
        # Parse 8-byte header
        timestamp_seconds = int.from_bytes(entry_data[0:4], byteorder='big')
        severity_byte = entry_data[4]
        flags_byte = entry_data[5]
        payload_length = int.from_bytes(entry_data[6:8], byteorder='big')
        
        # Extract severity level and subsystem ID
        severity_level = (severity_byte >> 4) & 0x0F
        subsystem_id = severity_byte & 0x0F
        
        # Extract payload
        payload = entry_data[8:8 + payload_length]
        message = payload.decode('utf-8', errors='replace')
        
        # Calculate timestamp
        timestamp = base_timestamp + timedelta(seconds=timestamp_seconds)
        timestamp_iso = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Create log record
        record = {
            "severity": severity_map.get(severity_level, "UNKNOWN"),
            "subsystem": subsystem_id,
            "timestamp": timestamp_iso,
            "message": message
        }
        
        log_records.append(record)
    
    return log_records