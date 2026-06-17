def deserialize_tpack_data(encoded_data: str) -> dict:
    """
    Deserialize TPACK (Tagged Packed) format data from base64-encoded string.
    
    TPACK is a binary format where data is encoded with type tags and length prefixes.
    This function decodes base64 input and parses the tagged binary structure into
    a Python dictionary.
    
    Utility:
        Converts base64-encoded TPACK binary data into human-readable Python dictionaries.
        Handles nested structures like customer info and item lists.
    
    Args:
        encoded_data (str): Base64-encoded TPACK binary data
    
    Returns:
        dict: Deserialized data structure containing all fields and nested objects
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
            
            # Type 0x00 = end of object
            if type_byte == 0x00:
                break
            
            # Read field name (length-prefixed string)
            if offset >= len(data):
                break
            name_len = data[offset]
            offset += 1
            
            if offset + name_len > len(data):
                break
            field_name = data[offset:offset + name_len].decode('utf-8', errors='ignore')
            offset += name_len
            
            # Parse value based on type
            if type_byte == 0x01:  # String
                if offset >= len(data):
                    break
                str_len = data[offset]
                offset += 1
                if offset + str_len > len(data):
                    break
                value = data[offset:offset + str_len].decode('utf-8', errors='ignore')
                offset += str_len
                result[field_name] = value
                
            elif type_byte == 0x02:  # Object/Dict
                nested_result, offset = parse_tpack(data, offset)
                result[field_name] = nested_result
                
            elif type_byte == 0x03:  # Integer
                if offset + 4 > len(data):
                    break
                value = struct.unpack('>I', data[offset:offset + 4])[0]
                offset += 4
                result[field_name] = value
                
            elif type_byte == 0x04:  # Array
                if offset >= len(data):
                    break
                array_len = data[offset]
                offset += 1
                array_items = []
                for _ in range(array_len):
                    if offset >= len(data):
                        break
                    item_type = data[offset]
                    offset += 1
                    if item_type == 0x02:  # Object in array
                        item, offset = parse_tpack(data, offset)
                        array_items.append(item)
                result[field_name] = array_items
                
            elif type_byte == 0x05:  # Float/Double
                if offset + 8 > len(data):
                    break
                value = struct.unpack('>d', data[offset:offset + 8])[0]
                offset += 8
                result[field_name] = value
        
        return result, offset
    
    deserialized, _ = parse_tpack(binary_data)
    return deserialized