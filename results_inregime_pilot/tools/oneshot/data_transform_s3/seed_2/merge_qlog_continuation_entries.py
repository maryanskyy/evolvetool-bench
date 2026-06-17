def merge_qlog_continuation_entries(base64_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    try:
        binary_data = base64.b64decode(base64_data)
    except Exception:
        return "Error: Invalid base64 data"
    
    if len(binary_data) < 2:
        return "Error: Data too short"
    
    merged_records = []
    current_record = None
    offset = 0
    
    while offset < len(binary_data):
        # Read entry header: 2 bytes for flags and length
        if offset + 2 > len(binary_data):
            break
        
        flags = binary_data[offset]
        entry_length = binary_data[offset + 1]
        offset += 2
        
        # Check if this is a continuation entry (bit 2 set)
        is_continuation = (flags & 0x04) != 0
        
        # Read entry data
        if offset + entry_length > len(binary_data):
            break
        
        entry_data = binary_data[offset:offset + entry_length]
        offset += entry_length
        
        # Parse entry data (severity, subsystem, timestamp, message)
        try:
            if len(entry_data) < 9:
                continue
            
            severity = entry_data[0]
            subsystem = entry_data[1]
            timestamp = struct.unpack('>Q', entry_data[2:10])[0]
            message = entry_data[10:].decode('utf-8', errors='replace')
            
            if is_continuation:
                # Merge with previous record
                if current_record is not None:
                    current_record['message'] += '\n' + message
            else:
                # Save previous record if exists
                if current_record is not None:
                    merged_records.append(current_record)
                
                # Start new record
                current_record = {
                    'severity': severity,
                    'subsystem': subsystem,
                    'timestamp': timestamp,
                    'message': message
                }
        except Exception:
            continue
    
    # Add last record
    if current_record is not None:
        merged_records.append(current_record)
    
    # Format output
    result = []
    for record in merged_records:
        result.append(f"Severity: {record['severity']}, Subsystem: {record['subsystem']}, Timestamp: {record['timestamp']}, Message: {record['message']}")
    
    return '\n---\n'.join(result) if result else "No records found"