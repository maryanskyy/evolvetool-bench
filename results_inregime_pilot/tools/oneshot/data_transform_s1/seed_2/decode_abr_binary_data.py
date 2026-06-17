def decode_abr_binary_data(base64_data: str) -> str:
    import base64
    import json
    
    # Decode base64 to binary
    binary_data = base64.b64decode(base64_data)
    
    records = []
    pos = 0
    
    while pos < len(binary_data):
        record = {}
        
        # Read records until we hit end of data
        while pos < len(binary_data):
            # Check for record marker (0x00 indicates field start)
            if binary_data[pos] == 0x00:
                pos += 1
                # Read field name length
                if pos >= len(binary_data):
                    break
                name_len = binary_data[pos]
                pos += 1
                
                # Read field name
                if pos + name_len > len(binary_data):
                    break
                field_name = binary_data[pos:pos + name_len].decode('utf-8', errors='ignore')
                pos += name_len
                
                # Read value length
                if pos >= len(binary_data):
                    break
                value_len = binary_data[pos]
                pos += 1
                
                # Read value
                if pos + value_len > len(binary_data):
                    break
                field_value = binary_data[pos:pos + value_len].decode('utf-8', errors='ignore')
                pos += value_len
                
                record[field_name] = field_value
            else:
                # Check if this is a record separator or end marker
                if binary_data[pos] == 0xFF or binary_data[pos] == 0x02:
                    pos += 1
                    if record:
                        records.append(record)
                    record = {}
                    if binary_data[pos - 1] == 0xFF:
                        break
                else:
                    pos += 1
        
        if record:
            records.append(record)
        break
    
    return json.dumps(records)