def decode_abr_base64_to_json(encoded_data: str) -> str:
    import base64
    import json
    
    # Decode base64
    decoded_bytes = base64.b64decode(encoded_data)
    
    records = []
    offset = 0
    
    while offset < len(decoded_bytes):
        record = {}
        
        # Read fields until we hit the next record marker or end
        while offset < len(decoded_bytes):
            # Check for record start marker (0x00)
            if decoded_bytes[offset] == 0x00:
                offset += 1
                break
            
            # Read field name length
            if offset >= len(decoded_bytes):
                break
            name_len = decoded_bytes[offset]
            offset += 1
            
            # Read field name
            if offset + name_len > len(decoded_bytes):
                break
            field_name = decoded_bytes[offset:offset + name_len].decode('utf-8')
            offset += name_len
            
            # Read field value length
            if offset >= len(decoded_bytes):
                break
            value_len = decoded_bytes[offset]
            offset += 1
            
            # Read field value
            if offset + value_len > len(decoded_bytes):
                break
            field_value = decoded_bytes[offset:offset + value_len].decode('utf-8')
            offset += value_len
            
            record[field_name] = field_value
        
        if record:
            records.append(record)
    
    return json.dumps(records)