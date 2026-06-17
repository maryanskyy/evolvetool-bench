def decode_abr_format(data: str) -> list:
    """
    Decode ABR (ARISE Binary Record) format data into a JSON-compatible list of objects.
    
    Utility:
        Parses binary-encoded records where each record contains key-value pairs.
        The format uses length-prefixed strings and type indicators to encode data.
    
    Args:
        data (str): Base64-encoded ABR format string
    
    Returns:
        list: List of dictionaries containing decoded records
    """
    import base64
    
    # Decode base64
    binary_data = base64.b64decode(data)
    
    records = []
    pos = 0
    
    while pos < len(binary_data):
        record = {}
        
        # Read number of fields in this record
        if pos >= len(binary_data):
            break
        
        num_fields = binary_data[pos]
        pos += 1
        
        # Read each field
        for _ in range(num_fields):
            if pos >= len(binary_data):
                break
            
            # Read key length and key
            key_len = binary_data[pos]
            pos += 1
            key = binary_data[pos:pos + key_len].decode('utf-8')
            pos += key_len
            
            # Read type indicator
            if pos >= len(binary_data):
                break
            type_indicator = binary_data[pos]
            pos += 1
            
            # Read value length and value
            if pos >= len(binary_data):
                break
            value_len = binary_data[pos]
            pos += 1
            value = binary_data[pos:pos + value_len].decode('utf-8')
            pos += value_len
            
            record[key] = value
        
        if record:
            records.append(record)
    
    return records