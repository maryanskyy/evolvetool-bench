def deserialize_tpack_data(encoded_data: str) -> dict:
    """
    Deserialize TPACK (Tagged Packed) format data from base64-encoded string.
    
    TPACK is a custom binary format where data is encoded with type tags and length prefixes.
    This function decodes base64 input and parses the tagged binary structure into a dictionary.
    
    Utility:
        Converts base64-encoded TPACK format data into a human-readable Python dictionary.
        Handles nested structures like customer info and item lists.
    
    Args:
        encoded_data (str): Base64-encoded TPACK data string
    
    Returns:
        dict: Deserialized data with all fields and nested structures
    """
    import base64
    import struct
    
    # Decode base64
    binary_data = base64.b64decode(encoded_data)
    
    result = {}
    pos = 0
    
    def read_type_and_length():
        nonlocal pos
        if pos >= len(binary_data):
            return None, None
        type_byte = binary_data[pos]
        pos += 1
        
        # Type byte encodes type in upper nibble, length in lower nibble
        data_type = (type_byte >> 4) & 0x0F
        length = type_byte & 0x0F
        
        # If length is 0x0F, next byte contains actual length
        if length == 0x0F:
            if pos >= len(binary_data):
                return data_type, 0
            length = binary_data[pos]
            pos += 1
        
        return data_type, length
    
    def read_string(length):
        nonlocal pos
        value = binary_data[pos:pos+length].decode('utf-8', errors='ignore')
        pos += length
        return value
    
    def read_float():
        nonlocal pos
        value = struct.unpack('>d', binary_data[pos:pos+8])[0]
        pos += 8
        return value
    
    def read_int(length):
        nonlocal pos
        if length == 1:
            value = binary_data[pos]
        elif length == 2:
            value = struct.unpack('>H', binary_data[pos:pos+2])[0]
        elif length == 4:
            value = struct.unpack('>I', binary_data[pos:pos+4])[0]
        else:
            value = int.from_bytes(binary_data[pos:pos+length], 'big')
        pos += length
        return value
    
    # Parse root level
    while pos < len(binary_data):
        data_type, length = read_type_and_length()
        if data_type is None:
            break
        
        # Read field name
        field_name = read_string(length)
        
        # Read field value
        value_type, value_length = read_type_and_length()
        if value_type is None:
            break
        
        if value_type == 0:  # String
            value = read_string(value_length)
        elif value_type == 1:  # Integer
            value = read_int(value_length)
        elif value_type == 2:  # List/Array
            items = []
            for _ in range(value_length):
                item = {}
                while True:
                    item_type, item_length = read_type_and_length()
                    if item_type is None or (item_type == 0 and item_length == 0):
                        break
                    item_field = read_string(item_length)
                    val_type, val_len = read_type_and_length()
                    if val_type == 0:
                        item[item_field] = read_string(val_len)
                    elif val_type == 1:
                        item[item_field] = read_int(val_len)
                    elif val_type == 3:
                        item[item_field] = read_float()
                if item:
                    items.append(item)
            value = items
        elif value_type == 3:  # Float
            value = read_float()
        else:
            value = None
        
        result[field_name] = value
    
    return result