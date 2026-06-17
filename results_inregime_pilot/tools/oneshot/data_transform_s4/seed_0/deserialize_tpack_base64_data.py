def deserialize_tpack_base64_data(base64_data):
    import base64
    import struct
    
    # Decode base64 to bytes
    binary_data = base64.b64decode(base64_data)
    
    def read_varint(data, offset):
        """Read a varint from binary data and return (value, new_offset)"""
        result = 0
        shift = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7f) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, offset
    
    def deserialize_value(data, offset, type_code):
        """Deserialize a value based on its type code"""
        if type_code == 0x00:  # Map
            size, offset = read_varint(data, offset)
            result = {}
            for _ in range(size):
                key_len, offset = read_varint(data, offset)
                key = data[offset:offset+key_len].decode('utf-8')
                offset += key_len
                value_type, offset = read_varint(data, offset)
                value, offset = deserialize_value(data, offset, value_type)
                result[key] = value
            return result, offset
        elif type_code == 0x01:  # String
            length, offset = read_varint(data, offset)
            value = data[offset:offset+length].decode('utf-8')
            offset += length
            return value, offset
        elif type_code == 0x02:  # Array
            size, offset = read_varint(data, offset)
            result = []
            for _ in range(size):
                elem_type, offset = read_varint(data, offset)
                value, offset = deserialize_value(data, offset, elem_type)
                result.append(value)
            return result, offset
        elif type_code == 0x03:  # Int32
            value = struct.unpack('<i', data[offset:offset+4])[0]
            offset += 4
            return value, offset
        elif type_code == 0x04:  # Uint16
            value = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            return value, offset
        elif type_code == 0x05:  # Uint8
            value = data[offset]
            offset += 1
            return value, offset
        else:
            return None, offset
    
    # Start deserialization from offset 0
    result, _ = deserialize_value(binary_data, 0, 0x00)
    
    import json
    return json.dumps(result, indent=2)