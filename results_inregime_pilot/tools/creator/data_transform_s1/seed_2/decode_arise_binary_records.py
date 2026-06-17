def decode_arise_binary_records(base64_data):
    """
    Decode ARISE Binary Record (ABR) format data.
    
    Utility:
        Parses base64-encoded binary data in ARISE format where records contain
        named fields with variable-length values. Records are separated by 0xFF bytes.
        Returns decoded records as a JSON-serializable list of dictionaries.
    
    Args:
        base64_data (str): Base64-encoded binary string in ARISE format
    
    Returns:
        list: List of dictionaries, each representing a decoded record with field names as keys
    """
    import base64
    import json
    
    # Decode base64 to binary
    binary_data = base64.b64decode(base64_data)
    
    records = []
    offset = 0
    
    while offset < len(binary_data):
        # Check for record separator
        if binary_data[offset] == 0xFF:
            offset += 1
            continue
        
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
    
    return records