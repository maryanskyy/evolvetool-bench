def decode_arise_binary_records(base64_data: str) -> str:
    import base64
    import json
    
    # Decode base64 to binary
    binary_data = base64.b64decode(base64_data)
    
    records = []
    offset = 0
    
    while offset < len(binary_data):
        # Check for record separator (0xFF)
        if offset > 0 and binary_data[offset] == 0xFF:
            offset += 1
            if offset >= len(binary_data):
                break
        
        # Read field count
        field_count = binary_data[offset]
        offset += 1
        
        record = {}
        
        # Read each field
        for _ in range(field_count):
            # Read field name length
            name_len = binary_data[offset]
            offset += 1
            
            # Read field name
            name = binary_data[offset:offset + name_len].decode('utf-8')
            offset += name_len
            
            # Read value length (2-byte big-endian)
            value_len = (binary_data[offset] << 8) | binary_data[offset + 1]
            offset += 2
            
            # Read value
            value = binary_data[offset:offset + value_len].decode('utf-8')
            offset += value_len
            
            record[name] = value
        
        records.append(record)
    
    return json.dumps(records)