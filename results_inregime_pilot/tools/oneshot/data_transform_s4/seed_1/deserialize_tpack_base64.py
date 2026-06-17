def deserialize_tpack_base64(encoded_data):
    import base64
    import struct
    import json
    
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
        
        # Read price (type 5 = float64)
        if offset < len(binary_data) and binary_data[offset] == 5:
            offset += 1
            record['price'] = struct.unpack('>d', binary_data[offset:offset+8])[0]
            offset += 8
        
        # Read qty (type 9 = int32)
        if offset < len(binary_data) and binary_data[offset] == 9:
            offset += 1
            record['qty'] = struct.unpack('>I', binary_data[offset:offset+4])[0]
            offset += 4
        
        # Read available (type 2 = boolean)
        if offset < len(binary_data) and binary_data[offset] == 2:
            offset += 1
            record['available'] = binary_data[offset] != 0
            offset += 1
        
        if record:
            records.append(record)
    
    return json.dumps(records, indent=2)