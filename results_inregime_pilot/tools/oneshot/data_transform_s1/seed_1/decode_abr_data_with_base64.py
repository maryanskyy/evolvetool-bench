def decode_abr_data_with_base64(encoded_data: str) -> str:
    import base64
    import json
    
    # Decode base64
    try:
        decoded_bytes = base64.b64decode(encoded_data)
    except Exception:
        return json.dumps([])
    
    records = []
    pos = 0
    
    while pos < len(decoded_bytes):
        record = {}
        
        # Read fields until we hit a marker or end
        while pos < len(decoded_bytes):
            # Check for field marker (0x00 indicates field separator)
            if decoded_bytes[pos] == 0x00:
                pos += 1
                # Read field name length
                if pos >= len(decoded_bytes):
                    break
                name_len = decoded_bytes[pos]
                pos += 1
                
                if pos + name_len > len(decoded_bytes):
                    break
                    
                field_name = decoded_bytes[pos:pos + name_len].decode('utf-8', errors='ignore')
                pos += name_len
                
                # Read field value length
                if pos >= len(decoded_bytes):
                    break
                value_len = decoded_bytes[pos]
                pos += 1
                
                if pos + value_len > len(decoded_bytes):
                    break
                    
                field_value = decoded_bytes[pos:pos + value_len].decode('utf-8', errors='ignore')
                pos += value_len
                
                record[field_name] = field_value
            else:
                # Try to parse as length-prefixed string
                if decoded_bytes[pos] == 0xFF:
                    pos += 1
                    if pos >= len(decoded_bytes):
                        break
                    # Record boundary marker
                    if record:
                        records.append(record)
                        record = {}
                    break
                else:
                    # Read as field name
                    name_len = decoded_bytes[pos]
                    pos += 1
                    if pos + name_len > len(decoded_bytes):
                        break
                    field_name = decoded_bytes[pos:pos + name_len].decode('utf-8', errors='ignore')
                    pos += name_len
                    
                    # Read value length
                    if pos >= len(decoded_bytes):
                        break
                    value_len = decoded_bytes[pos]
                    pos += 1
                    
                    if pos + value_len > len(decoded_bytes):
                        break
                    field_value = decoded_bytes[pos:pos + value_len].decode('utf-8', errors='ignore')
                    pos += value_len
                    
                    record[field_name] = field_value
        
        if record:
            records.append(record)
    
    return json.dumps(records)