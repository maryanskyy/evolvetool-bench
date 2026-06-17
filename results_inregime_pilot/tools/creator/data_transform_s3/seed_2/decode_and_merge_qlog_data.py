def decode_and_merge_qlog_data(encoded_data):
    """
    Decode QLOG data with continuation entries and merge them with parent entries.
    
    Utility:
        Decodes base64-encoded QLOG (QUIC Logging) data and merges continuation
        entries (those with flag bit 2 set) with their preceding non-continuation
        entry by appending messages with newline separators.
    
    Args:
        encoded_data (str): Base64-encoded QLOG data string
    
    Returns:
        list: List of dictionaries containing merged log records with keys:
              - severity: Log level (ERROR, WARNING, INFO, etc.)
              - subsystem: Subsystem identifier
              - timestamp: ISO format timestamp
              - message: Merged message text (with continuations appended)
    """
    import base64
    import struct
    from datetime import datetime, timezone
    
    # Decode base64 data
    decoded_bytes = base64.b64decode(encoded_data)
    
    # Parse QLOG format
    # Format: [flags(1)][severity(1)][subsystem(1)][timestamp(8)][message_len(2)][message]
    entries = []
    offset = 0
    
    while offset < len(decoded_bytes):
        if offset + 13 > len(decoded_bytes):
            break
        
        # Parse header
        flags = decoded_bytes[offset]
        severity = decoded_bytes[offset + 1]
        subsystem = decoded_bytes[offset + 2]
        timestamp_us = struct.unpack('>Q', decoded_bytes[offset + 3:offset + 11])[0]
        message_len = struct.unpack('>H', decoded_bytes[offset + 11:offset + 13])[0]
        
        offset += 13
        
        # Extract message
        if offset + message_len > len(decoded_bytes):
            break
        
        message = decoded_bytes[offset:offset + message_len].decode('utf-8', errors='replace')
        offset += message_len
        
        # Convert timestamp (microseconds since epoch to ISO format)
        timestamp_sec = timestamp_us / 1_000_000
        dt = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
        timestamp_str = dt.isoformat().replace('+00:00', 'Z')
        
        # Map severity codes
        severity_map = {0: 'DEBUG', 1: 'INFO', 2: 'WARNING', 3: 'ERROR'}
        severity_str = severity_map.get(severity, f'LEVEL_{severity}')
        
        # Check if this is a continuation entry (flag bit 2 set)
        is_continuation = bool(flags & 0x04)
        
        entry = {
            'severity': severity_str,
            'subsystem': subsystem,
            'timestamp': timestamp_str,
            'message': message,
            'is_continuation': is_continuation
        }
        
        entries.append(entry)
    
    # Merge continuation entries with their parent
    merged_entries = []
    for entry in entries:
        if entry['is_continuation'] and merged_entries:
            # Append to previous entry's message
            merged_entries[-1]['message'] += '\n' + entry['message']
        else:
            # Add as new entry (remove the internal flag)
            clean_entry = {
                'severity': entry['severity'],
                'subsystem': entry['subsystem'],
                'timestamp': entry['timestamp'],
                'message': entry['message']
            }
            merged_entries.append(clean_entry)
    
    return merged_entries