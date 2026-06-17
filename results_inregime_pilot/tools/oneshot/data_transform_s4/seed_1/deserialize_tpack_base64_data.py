def deserialize_tpack_base64_data(encoded_data: str) -> str:
    import base64
    import struct
    import json
    
    # Decode base64
    binary_data = base64.b64decode(encoded_data)
    
    result = {}
    offset = 0
    
    def read_byte():
        nonlocal offset
        val = binary_data[offset]
        offset += 1
        return val
    
    def read_string():
        nonlocal offset
        length = read_byte()
        val = binary_data[offset:offset+length].decode('utf-8')
        offset += length
        return val
    
    def read_value():
        type_byte = read_byte()
        if type_byte == 0x01:  # String
            return read_string()
        elif type_byte == 0x02:  # Boolean
            return bool(read_byte())
        elif type_byte == 0x03:  # Integer
            return read_byte()
        elif type_byte == 0x04:  # Float
            val = struct.unpack('>d', binary_data[offset:offset+8])[0]
            offset_val = offset + 8
            return val
        elif type_byte == 0x05:  # Array
            count = read_byte()
            arr = []
            for _ in range(count):
                arr.append(read_value())
            return arr
        elif type_byte == 0x06:  # Object
            obj = {}
            count = read_byte()
            for _ in range(count):
                key = read_string()
                obj[key] = read_value()
            return obj
        return None
    
    # Parse root object
    root_type = read_byte()
    if root_type == 0x06:  # Object
        count = read_byte()
        for _ in range(count):
            key = read_string()
            result[key] = read_value()
    
    return json.dumps(result, indent=2)