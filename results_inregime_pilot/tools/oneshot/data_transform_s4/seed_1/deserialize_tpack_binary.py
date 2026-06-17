def deserialize_tpack_binary(base64_data):
    import base64
    import struct
    import json
    
    data = base64.b64decode(base64_data)
    
    def read_varint(offset):
        """Read a varint and return (value, new_offset)"""
        result = 0
        shift = 0
        while True:
            byte = data[offset]
            result |= (byte & 0x7F) << shift
            offset += 1
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, offset
    
    def parse_value(offset):
        """Parse a value starting at offset and return (value, new_offset)"""
        tag = data[offset]
        offset += 1
        
        if tag == 0x01:
            return None, offset
        elif tag == 0x02:
            return False, offset
        elif tag == 0x03:
            return True, offset
        elif tag == 0x10:
            return data[offset], offset + 1
        elif tag == 0x11:
            value = struct.unpack('>H', data[offset:offset+2])[0]
            return value, offset + 2
        elif tag == 0x12:
            value = struct.unpack('>i', data[offset:offset+4])[0]
            return value, offset + 4
        elif tag == 0x13:
            value = struct.unpack('>d', data[offset:offset+8])[0]
            return value, offset + 8
        elif tag == 0x20:
            length, offset = read_varint(offset)
            value = data[offset:offset+length].decode('utf-8')
            return value, offset + length
        elif tag == 0x30:
            count, offset = read_varint(offset)
            array = []
            for _ in range(count):
                value, offset = parse_value(offset)
                array.append(value)
            return array, offset
        elif tag == 0x40:
            count, offset = read_varint(offset)
            obj = {}
            for _ in range(count):
                key_len, offset = read_varint(offset)
                key = data[offset:offset+key_len].decode('utf-8')
                offset += key_len
                value, offset = parse_value(offset)
                obj[key] = value
            return obj, offset
        else:
            raise ValueError(f'Unknown tag: {hex(tag)}')
    
    result, _ = parse_value(0)
    return json.dumps(result)