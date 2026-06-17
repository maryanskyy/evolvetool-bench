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
        
        severity_byte = binary_data[0]
        subsystem = binary_data[1]
        timestamp_bytes = binary_data[2:6]
        message_bytes = binary_data[6:]
        
        # Unpack timestamp (big-endian unsigned int)
        timestamp = struct.unpack('>I', timestamp_bytes)[0]
        
        # Map severity codes
        severity_map = {0: 'DEBUG', 1: 'INFO', 2: 'WARN', 3: 'ERROR', 4: 'CRITICAL'}
        severity = severity_map.get(severity_byte, f'UNKNOWN({severity_byte})')
        
        # Decode message
        message = message_bytes.decode('utf-8', errors='replace')
        
        # Format timestamp (Unix epoch to ISO format approximation)
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        iso_timestamp = dt.isoformat().replace('+00:00', 'Z')
        
        # Return formatted record
        result = f"Severity: {severity}\nSubsystem: {subsystem}\nTimestamp: {iso_timestamp}\nMessage: {message}"
        return result
    except Exception as e:
        return f"Error parsing QLOG data: {str(e)}"