def decode_abr_format(encoded_data: str) -> str:
    import base64
    import json
    
    # Decode base64
    decoded_bytes = base64.b64decode(encoded_data)
    
    records = []
    pos = 0
    
    while pos < len(decoded_bytes):
        record = {}
        
        # Read fields until we hit a marker for next record or end
        while pos < len(decoded_bytes):
            # Read field type byte
            field_type = decoded_bytes[pos]
            pos += 1
            
            # Read field name length
            name_len = decoded_bytes[pos]
            pos += 1
            
            # Read field name
            field_name = decoded_bytes[pos:pos + name_len].decode('utf-8')
            pos += name_len
            
            # Read field value length (2 bytes, big-endian)
            value_len = (decoded_bytes[pos] << 8) | decoded_bytes[pos + 1]
            pos += 2
            
            # Read field value
            field_value = decoded_bytes[pos:pos + value_len].decode('utf-8')
            pos += value_len
            
            record[field_name] = field_value
            
            # Check if next byte indicates new record (0xFF) or end
            if pos < len(decoded_bytes) and decoded_bytes[pos] == 0xFF:
                pos += 1
                break
            elif pos >= len(decoded_bytes):
                break
        
        if record:
            records.append(record)
    
    return json.dumps(records)