def parse_qlog_base64_to_records(base64_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64 string
        binary_data = base64.b64decode(base64_data)
        
        # Parse binary QLOG format
        # Format: 1 byte severity, 1 byte subsystem, 4 bytes timestamp, rest is message
        if len(binary_data) < 6:
            return "Error: Invalid QLOG data format"
        
        severity = binary_data[0]
        subsystem = binary_data[1]
        timestamp_bytes = binary_data[2:6]
        timestamp = struct.unpack('>I', timestamp_bytes)[0]
        message = binary_data[6:].decode('utf-8', errors='ignore')
        
        # Map severity levels
        severity_map = {0: 'DEBUG', 1: 'INFO', 2: 'WARN', 3: 'ERROR', 4: 'CRITICAL'}
        severity_str = severity_map.get(severity, f'UNKNOWN({severity})')
        
        # Format timestamp (Unix timestamp to ISO format approximation)
        from datetime import datetime, timezone
        try:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            timestamp_str = dt.isoformat() + 'Z'
        except:
            timestamp_str = str(timestamp)
        
        # Build output record
        record = f"Severity: {severity_str}\nSubsystem: {subsystem}\nTimestamp: {timestamp_str}\nMessage: {message}"
        return record
    except Exception as e:
        return f"Error parsing QLOG data: {str(e)}"