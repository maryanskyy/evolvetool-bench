def deserialize_tpack_base64(encoded_data):
    import base64
    import struct
    
    # Decode base64
    binary_data = base64.b64decode(encoded_data)
    
    records = []
    offset = 0
    
    while offset < len(binary_data):
        record = {}
        
        # Read SKU (type 3 = string)
        if offset < len(binary_data) and binary_data[offset] == 3:
            offset += 1
            str_len = binary_data[offset]
            offset += 1
            record['sku'] = binary_data[offset:offset+str_len].decode('utf-8')
            offset += str_len
        
        # Read name (type 4 = string)
        if offset < len(binary_data) and binary_data[offset] == 4:
            offset += 1
            str_len = binary_data[offset]
            offset += 1
            record['name'] = binary_data[offset:offset+str_len].decode('utf-8')
            offset += str_len
        
        # Read price (type 19 = float)
        if offset < len(binary_data) and binary_data[offset] == 19:
            offset += 1
            record['price'] = struct.unpack('>f', binary_data[offset:offset+4])[0]
            offset += 4
        
        # Read qty (type 16 = int)
        if offset < len(binary_data) and binary_data[offset] == 16:
            offset += 1
            record['qty'] = struct.unpack('>I', binary_data[offset:offset+4])[0]
            offset += 4
        
        # Read available (type 2 or 3 = boolean)
        if offset < len(binary_data) and binary_data[offset] in (2, 3):
            offset += 1
            record['available'] = bool(binary_data[offset])
            offset += 1
        
        if record:
            records.append(record)
    
    import json
    return json.dumps(records, indent=2)