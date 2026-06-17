def deserialize_tpack_data(encoded_data: str) -> dict:
    """
    Deserialize TPACK (Tagged Packed) format data from base64 encoding.
    
    TPACK is a binary format where data is encoded with type tags and length prefixes.
    This function decodes base64 input and parses the tagged binary structure into
    a Python dictionary.
    
    Utility:
        Converts base64-encoded TPACK binary data into human-readable Python dictionaries,
        handling nested structures like customer info and item lists.
    
    Args:
        encoded_data (str): Base64-encoded TPACK binary data
    
    Returns:
        dict: Deserialized data structure with all fields and nested objects
    """
    import base64
    import struct
    
    # Decode base64
    binary_data = base64.b64decode(encoded_data)
    
    def parse_tpack(data: bytes, offset: int = 0) -> tuple:
        """Parse TPACK binary format recursively."""
        result = {}
        
        while offset < len(data):
            # Read type byte
            if offset >= len(data):
                break
                
            type_byte = data[offset]
            offset += 1
            
            # Read key length and key
            if offset >= len(data):
                break
            key_len = data[offset]
            offset += 1
            
            if offset + key_len > len(data):
                break
            key = data[offset:offset + key_len].decode('utf-8', errors='ignore')
            offset += key_len
            
            # Parse value based on type
            if type_byte == 0x01:  # String
                if offset >= len(data):
                    break
                val_len = data[offset]
                offset += 1
                if offset + val_len > len(data):
                    break
                value = data[offset:offset + val_len].decode('utf-8', errors='ignore')
                offset += val_len
                result[key] = value
                
            elif type_byte == 0x02:  # Object/Dict
                if offset >= len(data):
                    break
                obj_len = data[offset]
                offset += 1
                obj_data = data[offset:offset + obj_len]
                offset += obj_len
                value, _ = parse_tpack(obj_data, 0)
                result[key] = value
                
            elif type_byte == 0x03:  # Integer
                if offset + 4 > len(data):
                    break
                value = struct.unpack('>I', data[offset:offset + 4])[0]
                offset += 4
                result[key] = value
                
            elif type_byte == 0x04:  # Float/Double
                if offset + 8 > len(data):
                    break
                value = struct.unpack('>d', data[offset:offset + 8])[0]
                offset += 8
                result[key] = value
                
            elif type_byte == 0x05:  # Array
                if offset >= len(data):
                    break
                arr_len = data[offset]
                offset += 1
                array = []
                for _ in range(arr_len):
                    if offset >= len(data):
                        break
                    item_type = data[offset]
                    offset += 1
                    
                    if item_type == 0x02:  # Object in array
                        if offset >= len(data):
                            break
                        obj_size = data[offset]
                        offset += 1
                        obj_data = data[offset:offset + obj_size]
                        offset += obj_size
                        item, _ = parse_tpack(obj_data, 0)
                        array.append(item)
                    elif item_type == 0x03:  # Integer in array
                        if offset + 4 > len(data):
                            break
                        value = struct.unpack('>I', data[offset:offset + 4])[0]
                        offset += 4
                        array.append(value)
                        
                result[key] = array
        
        return result, offset
    
    parsed_data, _ = parse_tpack(binary_data)
    return parsed_data