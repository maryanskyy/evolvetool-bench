def decode_abr_format(encoded_data: str) -> str:
    import base64
    import json
    
    # Decode base64
    binary_data = base64.b64decode(encoded_data)
    
    records = []
    offset = 0
    
    while offset < len(binary_data):
        record = {}
        
        # Parse fields until we hit a record separator or end
        while offset < len(binary_data):
            # Read field type byte
            if offset >= len(binary_data):
                break
            
            field_type = binary_data[offset]
            offset += 1
            
            # Read key length and key
            if offset >= len(binary_data):
                break
            key_len = binary_data[offset]
            offset += 1
            
            if offset + key_len > len(binary_data):
                break
            key = binary_data[offset:offset + key_len].decode('utf-8')
            offset += key_len
            
            # Read value length and value
            if offset >= len(binary_data):
                break
            val_len = binary_data[offset]
            offset += 1
            
            if offset + val_len > len(binary_data):
                break
            value = binary_data[offset:offset + val_len].decode('utf-8')
            offset += val_len
            
            record[key] = value
            
            # Check for record separator (0xFF)
            if offset < len(binary_data) and binary_data[offset] == 0xFF:
                offset += 1
                break
        
        if record:
            records.append(record)
        
        if offset >= len(binary_data):
            break
    
    return json.dumps(records)