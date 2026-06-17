def deserialize_and_filter_tpack(encoded_data):
    """
    Deserialize TPACK-encoded data and filter records where 'available' is True.
    
    Utility:
        Decodes base64-encoded TPACK (Tagged Packed) format data and extracts
        product records, returning only those with available=True.
    
    Args:
        encoded_data (str): Base64-encoded TPACK data string
    
    Returns:
        list: List of dictionaries containing filtered product records where available is True
    """
    import base64
    import struct
    
    # Decode base64
    decoded = base64.b64decode(encoded_data)
    
    records = []
    offset = 0
    
    while offset < len(decoded):
        record = {}
        
        # Read tag-length-value format
        while offset < len(decoded):
            tag = decoded[offset]
            offset += 1
            
            if tag == 0x03:  # End of record marker
                break
            
            # Read length
            length = decoded[offset]
            offset += 1
            
            # Read value based on tag
            if tag == 0x03:  # sku (string)
                value = decoded[offset:offset+length].decode('utf-8')
                record['sku'] = value
                offset += length
            elif tag == 0x04:  # name (string)
                value = decoded[offset:offset+length].decode('utf-8')
                record['name'] = value
                offset += length
            elif tag == 0x05:  # price (float)
                value = struct.unpack('>f', decoded[offset:offset+length])[0]
                record['price'] = value
                offset += length
            elif tag == 0x09:  # qty (int)
                value = struct.unpack('>H', decoded[offset:offset+length])[0]
                record['qty'] = value
                offset += length
            elif tag == 0x0A:  # available (boolean)
                value = decoded[offset] != 0
                record['available'] = value
                offset += 1
            else:
                offset += length
        
        if record:
            records.append(record)
    
    # Filter for available=True
    filtered = [r for r in records if r.get('available', False)]
    
    return filtered