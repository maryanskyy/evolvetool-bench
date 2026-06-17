def decode_qlog_binary(base64_data):
    import base64
    from datetime import datetime, timedelta
    
    # Decode base64
    binary_data = base64.b64decode(base64_data)
    
    # Severity level names
    severity_names = ['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL']
    
    # Base timestamp: 2025-01-01 00:00:00 UTC
    base_timestamp = datetime(2025, 1, 1, 0, 0, 0)
    
    records = []
    i = 0
    
    while i < len(binary_data):
        # Check for separator marker 0xFE 0xFE
        if i > 0 and i + 1 < len(binary_data) and binary_data[i] == 0xFE and binary_data[i + 1] == 0xFE:
            i += 2
            continue
        
        # Need at least 8 bytes for header
        if i + 8 > len(binary_data):
            break
        
        # Parse header
        timestamp_seconds = int.from_bytes(binary_data[i:i+4], byteorder='big')
        severity_byte = binary_data[i+4]
        flags_byte = binary_data[i+5]
        payload_length = int.from_bytes(binary_data[i+6:i+8], byteorder='big')
        
        # Extract severity level and subsystem
        severity_level = (severity_byte >> 4) & 0x0F
        subsystem_id = severity_byte & 0x0F
        
        # Calculate timestamp
        timestamp = base_timestamp + timedelta(seconds=timestamp_seconds)
        timestamp_iso = timestamp.isoformat() + 'Z'
        
        # Extract payload
        payload_start = i + 8
        payload_end = payload_start + payload_length
        
        if payload_end > len(binary_data):
            break
        
        message = binary_data[payload_start:payload_end].decode('utf-8', errors='replace')
        
        # Get severity name
        severity_name = severity_names[severity_level] if severity_level < len(severity_names) else 'UNKNOWN'
        
        # Create record
        record = {
            'severity': severity_name,
            'subsystem': subsystem_id,
            'timestamp': timestamp_iso,
            'message': message
        }
        records.append(record)
        
        # Move to next entry
        i = payload_end
    
    # Convert to JSON string
    import json
    return json.dumps(records, indent=2)