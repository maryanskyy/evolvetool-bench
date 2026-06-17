def deserialize_tpack(base64_data):
    """
    Deserialize TPACK (Tagged Pack Format) binary data into Python objects.
    
    Utility:
        Parses base64-encoded TPACK binary format into native Python data structures.
        Supports null, booleans, integers, floats, strings, arrays, and maps.
    
    Args:
        base64_data (str): Base64-encoded TPACK binary data
    
    Returns:
        Deserialized Python object (dict, list, str, int, float, bool, or None)
    """
    import base64
    import struct
    
    data = base64.b64decode(base64_data)
    
    def parse_varint(offset):
        """Parse a varint and return (value, new_offset)"""
        value = 0
        shift = 0
        while True:
            byte = data[offset]
            value |= (byte & 0x7F) << shift
            offset += 1
            if (byte & 0x80) == 0:
                break
            shift += 7
        return value, offset
    
    def parse_value(offset):
        """Parse a value starting at offset and return (value, new_offset)"""
        tag = data[offset]
        offset += 1
        
        if tag == 0x01:  # null
            return None, offset
        elif tag == 0x02:  # false
            return False, offset
        elif tag == 0x03:  # true
            return True, offset
        elif tag == 0x10:  # uint8
            return data[offset], offset + 1
        elif tag == 0x11:  # uint16
            value = struct.unpack('>H', data[offset:offset+2])[0]
            return value, offset + 2
        elif tag == 0x12:  # int32
            value = struct.unpack('>i', data[offset:offset+4])[0]
            return value, offset + 4
        elif tag == 0x13:  # float64
            value = struct.unpack('>d', data[offset:offset+8])[0]
            return value, offset + 8
        elif tag == 0x20:  # string
            length, offset = parse_varint(offset)
            value = data[offset:offset+length].decode('utf-8')
            return value, offset + length
        elif tag == 0x30:  # array
            count, offset = parse_varint(offset)
            array = []
            for _ in range(count):
                value, offset = parse_value(offset)
                array.append(value)
            return array, offset
        elif tag == 0x40:  # map
            count, offset = parse_varint(offset)
            map_dict = {}
            for _ in range(count):
                # Keys are always strings
                key_length, offset = parse_varint(offset)
                key = data[offset:offset+key_length].decode('utf-8')
                offset += key_length
                # Parse value
                value, offset = parse_value(offset)
                map_dict[key] = value
            return map_dict, offset
        else:
            raise ValueError(f"Unknown tag: 0x{tag:02x}")
    
    result, _ = parse_value(0)
    return result