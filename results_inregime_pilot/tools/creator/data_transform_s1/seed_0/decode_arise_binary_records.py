def decode_arise_binary_records(base64_data):
    """
    Decode ARISE Binary Record (ABR) format data.
    
    Utility:
        Parses base64-encoded binary data in ARISE format where records contain
        key-value field pairs. Records are separated by 0xFF bytes. Each record
        starts with a field count byte, followed by fields with name-value pairs.
    
    Args:
        base64_data (str): Base64-encoded binary string in ARISE format
    
    Returns:
        list: Array of dictionaries, each representing a decoded record with
              field names as keys and field values as string values
    """
    import base64
    
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
            field_name = binary_data[offset:offset + name_len].decode('utf-8')
            offset += name_len
            
            # Read value length (2-byte big-endian)
            value_len = (binary_data[offset] << 8) | binary_data[offset + 1]
            offset += 2
            
            # Read field value
            field_value = binary_data[offset:offset + value_len].decode('utf-8')
            offset += value_len
            
            record[field_name] = field_value
        
        records.append(record)
    
    return records