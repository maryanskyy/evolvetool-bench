def decode_and_count_qlog_severity(encoded_data: str) -> str:
    import base64
    import json
    
    # Decode the base64 string
    try:
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode('utf-8')
    except Exception:
        return json.dumps({})
    
    # Parse QLOG format: entries are separated by specific markers
    # Each entry contains severity info and message
    severity_counts = {}
    
    # Split by common QLOG delimiters and parse entries
    lines = decoded_str.split('\x00')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Determine severity based on keywords in the message
        severity = None
        line_lower = line.lower()
        
        if 'error' in line_lower or 'failed' in line_lower or 'timeout' in line_lower:
            severity = 'ERROR'
        elif 'warn' in line_lower or 'slow' in line_lower:
            severity = 'WARN'
        elif 'started' in line_lower or 'established' in line_lower or 'retrying' in line_lower:
            severity = 'INFO'
        
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    return json.dumps(severity_counts)