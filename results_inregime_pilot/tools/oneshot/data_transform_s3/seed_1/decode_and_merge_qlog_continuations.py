def decode_and_merge_qlog_continuations(base64_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    try:
        binary_data = base64.b64decode(base64_data)
    except Exception as e:
        return f"Error decoding base64: {e}"
    
    records = []
    offset = 0
    
    # Parse QLOG binary format
    while offset < len(binary_data):
        if offset + 8 > len(binary_data):
            break
        
        # Read header: timestamp (4 bytes), flags (1 byte), severity (1 byte), subsystem (1 byte), message_len (1 byte)
        timestamp = struct.unpack('>I', binary_data[offset:offset+4])[0]
        flags = binary_data[offset+4]
        severity = binary_data[offset+5]
        subsystem = binary_data[offset+6]
        message_len = binary_data[offset+7]
        offset += 8
        
        # Read message
        if offset + message_len > len(binary_data):
            break
        message = binary_data[offset:offset+message_len].decode('utf-8', errors='replace')
        offset += message_len
        
        # Check if this is a continuation entry (bit 2 of flags set)
        is_continuation = bool(flags & 0x04)
        
        record = {
            'timestamp': timestamp,
            'flags': flags,
            'severity': severity,
            'subsystem': subsystem,
            'message': message,
            'is_continuation': is_continuation
        }
        records.append(record)
    
    # Merge continuation entries with their preceding entries
    merged_records = []
    for record in records:
        if record['is_continuation'] and merged_records:
            # Append to previous record's message with newline separator
            merged_records[-1]['message'] += '\n' + record['message']
        else:
            # Add as new record
            merged_records.append(record)
    
    # Format output
    result_lines = []
    for record in merged_records:
        result_lines.append(f"Timestamp: {record['timestamp']}, Severity: {record['severity']}, Subsystem: {record['subsystem']}, Message: {record['message']}")
    
    return '\n'.join(result_lines)