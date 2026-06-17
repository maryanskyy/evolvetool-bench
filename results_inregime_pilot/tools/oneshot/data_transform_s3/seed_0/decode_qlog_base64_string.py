def decode_qlog_base64_string(encoded_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        
        records = []
        offset = 0
        
        while offset < len(decoded_bytes):
            # Parse record header (4 bytes: severity, subsystem, timestamp)
            if offset + 4 > len(decoded_bytes):
                break
            
            severity_byte = decoded_bytes[offset]
            subsystem_byte = decoded_bytes[offset + 1]
            timestamp_bytes = decoded_bytes[offset + 2:offset + 4]
            offset += 4
            
            # Parse message length (2 bytes, big-endian)
            if offset + 2 > len(decoded_bytes):
                break
            
            msg_len = struct.unpack('>H', decoded_bytes[offset:offset + 2])[0]
            offset += 2
            
            # Parse message
            if offset + msg_len > len(decoded_bytes):
                break
            
            message = decoded_bytes[offset:offset + msg_len].decode('utf-8', errors='ignore')
            offset += msg_len
            
            # Map severity codes
            severity_map = {0: 'FATAL', 1: 'ERROR', 2: 'WARN', 3: 'INFO', 4: 'DEBUG', 5: 'TRACE'}
            severity = severity_map.get(severity_byte, f'UNKNOWN({severity_byte})')
            
            records.append({
                'severity': severity,
                'subsystem': subsystem_byte,
                'message': message
            })
        
        # Format output as table
        result = '| Severity | Subsystem | Message |\n'
        result += '|----------|-----------|---------|\n'
        for record in records:
            result += f"| {record['severity']} | {record['subsystem']} | {record['message']} |\n"
        
        return result
    
    except Exception as e:
        return f'Error decoding QLOG data: {str(e)}'