def deserialize_tpack(base64_data):
    """
    Deserialize TPACK (Tagged Pack Format) binary data into Python objects.
    
    Utility:
        Decodes Base64-encoded TPACK binary format into native Python data structures.
        Supports null, booleans, integers, floats, strings, arrays, and maps.
    
    Args:
        base64_data (str): Base64-encoded TPACK binary data
    
    Returns:
        Deserialized Python object (can be dict, list, str, int, float, bool, or None)
    """
    import base64
    import struct
    
    # Decode base64
    binary_data = base64.b64decode(base64_data)
    
    def decode_varint(data, offset):
        """Decode a varint and return (value, new_offset)"""
        result = 0
        shift = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, offset
    
    def deserialize_value(data, offset):
        """Deserialize a single value and return (value, new_offset)"""
        if offset >= len(data):
            return None, offset
        
        type_tag = data[offset]
        offset += 1
        
        # Null, false, true
        if type_tag == 0x01:
            return None, offset
        elif type_tag == 0x02:
            return False, offset
        elif type_tag == 0x03:
            return True, offset
        
        # Unsigned integers
        elif type_tag == 0x10:  # uint8
            return data[offset], offset + 1
        elif type_tag == 0x11:  # uint16
            value = struct.unpack('>H', data[offset:offset+2])[0]
            return value, offset + 2
        
        # Signed integer
        elif type_tag == 0x12:  # int32
            value = struct.unpack('>i', data[offset:offset+4])[0]
            return value, offset + 4
        
        # Float
        elif type_tag == 0x13:  # float64
            value = struct.unpack('>d', data[offset:offset+8])[0]
            return value, offset + 8
        
        # String
        elif type_tag == 0x20:
            length, offset = decode_varint(data, offset)
            value = data[offset:offset+length].decode('utf-8')
            return value, offset + length
        
        # Array
        elif type_tag == 0x30:
            count, offset = decode_varint(data, offset)
            array = []
            for _ in range(count):
                value, offset = deserialize_value(data, offset)
                array.append(value)
            return array, offset
        
        # Map
        elif type_tag == 0x40:
            count, offset = decode_varint(data, offset)
            map_obj = {}
            for _ in range(count):
                # Keys are always strings
                key, offset = deserialize_value(data, offset)
                value, offset = deserialize_value(data, offset)
                map_obj[key] = value
            return map_obj, offset
        
        return None, offset
    
    result, _ = deserialize_value(binary_data, 0)
    return result