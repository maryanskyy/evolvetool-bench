def merge_qlog_continuation_entries(base64_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    try:
        binary_data = base64.b64decode(base64_data)
    except Exception as e:
        return f"Error decoding base64: {e}"
    
    if len(binary_data) < 4:
        return "Error: insufficient data"
    
    merged_records = []
    offset = 0
    current_record = None
    
    while offset < len(binary_data):
        # Read entry header (minimum 4 bytes: flags + length)
        if offset + 4 > len(binary_data):
            break
        
        flags = binary_data[offset]
        entry_length = struct.unpack('>I', b'\x00' + binary_data[offset+1:offset+4])[0]
        offset += 4
        
        if offset + entry_length > len(binary_data):
            break
        
        entry_data = binary_data[offset:offset+entry_length]
        offset += entry_length
        
        # Check if this is a continuation entry (bit 2 set)
        is_continuation = bool(flags & 0x04)
        
        if is_continuation:
            # Merge with previous record
            if current_record is not None:
                # Extract message from continuation entry
                try:
                    message = entry_data.decode('utf-8', errors='replace')
                    current_record['message'] += '\n' + message
                except:
                    pass
        else:
            # Save previous record if exists
            if current_record is not None:
                merged_records.append(current_record)
            
            # Parse new non-continuation entry
            try:
                # Parse severity (1 byte), subsystem (1 byte), timestamp (8 bytes), message (rest)
                if len(entry_data) >= 10:
                    severity = entry_data[0]
                    subsystem = entry_data[1]
                    timestamp = struct.unpack('>Q', entry_data[2:10])[0]
                    message = entry_data[10:].decode('utf-8', errors='replace')
                    
                    current_record = {
                        'severity': severity,
                        'subsystem': subsystem,
                        'timestamp': timestamp,
                        'message': message
                    }
            except:
                pass
    
    # Add last record
    if current_record is not None:
        merged_records.append(current_record)
    
    # Format output
    result = []
    for record in merged_records:
        result.append(f"Severity: {record['severity']}, Subsystem: {record['subsystem']}, Timestamp: {record['timestamp']}, Message: {record['message']}")
    
    return '\n---\n'.join(result) if result else "No records found"