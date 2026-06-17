def deserialize_tpack_data(encoded_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    binary_data = base64.b64decode(encoded_data)
    
    result = {}
    pos = 0
    
    def read_byte():
        nonlocal pos
        val = binary_data[pos]
        pos += 1
        return val
    
    def read_bytes(n):
        nonlocal pos
        val = binary_data[pos:pos+n]
        pos += n
        return val
    
    def read_string():
        length = read_byte()
        return read_bytes(length).decode('utf-8')
    
    def read_float():
        data = read_bytes(8)
        return struct.unpack('>d', data)[0]
    
    def read_int():
        return read_byte()
    
    def read_bool():
        return read_byte() != 0
    
    # Parse key-value pairs
    while pos < len(binary_data):
        key_len = read_byte()
        if key_len == 0:
            break
        key = read_bytes(key_len).decode('utf-8')
        type_byte = read_byte()
        
        if type_byte == 1:  # string
            value = read_string()
        elif type_byte == 2:  # boolean
            value = read_bool()
        elif type_byte == 3:  # int
            value = read_int()
        elif type_byte == 4:  # float
            value = read_float()
        elif type_byte == 5:  # array
            value = []
            array_len = read_byte()
            for _ in range(array_len):
                item = {}
                item_type = read_byte()
                while True:
                    item_key_len = read_byte()
                    if item_key_len == 0:
                        break
                    item_key = read_bytes(item_key_len).decode('utf-8')
                    item_type_byte = read_byte()
                    if item_type_byte == 1:
                        item[item_key] = read_string()
                    elif item_type_byte == 3:
                        item[item_key] = read_int()
                    elif item_type_byte == 4:
                        item[item_key] = read_float()
                value.append(item)
        else:
            value = None
        
        result[key] = value
    
    import json
    return json.dumps(result, indent=2)