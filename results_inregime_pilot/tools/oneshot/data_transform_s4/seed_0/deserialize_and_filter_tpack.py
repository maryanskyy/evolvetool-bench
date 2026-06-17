def deserialize_and_filter_tpack(encoded_data: str) -> str:
    import base64
    import struct
    
    # Decode base64
    try:
        binary_data = base64.b64decode(encoded_data)
    except Exception as e:
        return f"Error decoding base64: {str(e)}"
    
    records = []
    offset = 0
    
    try:
        while offset < len(binary_data):
            record = {}
            
            # Read fields until we hit a record separator or end
            while offset < len(binary_data):
                # Read field type byte
                if offset >= len(binary_data):
                    break
                    
                field_type = binary_data[offset]
                offset += 1
                
                # Read field name length and name
                if offset >= len(binary_data):
                    break
                name_len = binary_data[offset]
                offset += 1
                
                if offset + name_len > len(binary_data):
                    break
                field_name = binary_data[offset:offset + name_len].decode('utf-8', errors='ignore')
                offset += name_len
                
                # Parse value based on type
                if field_type == 3:  # String
                    if offset >= len(binary_data):
                        break
                    val_len = binary_data[offset]
                    offset += 1
                    if offset + val_len > len(binary_data):
                        break
                    value = binary_data[offset:offset + val_len].decode('utf-8', errors='ignore')
                    offset += val_len
                    record[field_name] = value
                elif field_type == 19:  # Float (4 bytes)
                    if offset + 4 > len(binary_data):
                        break
                    value = struct.unpack('>f', binary_data[offset:offset + 4])[0]
                    offset += 4
                    record[field_name] = value
                elif field_type == 16:  # Integer (2 bytes)
                    if offset + 2 > len(binary_data):
                        break
                    value = struct.unpack('>H', binary_data[offset:offset + 2])[0]
                    offset += 2
                    record[field_name] = value
                elif field_type == 2:  # Boolean
                    if offset >= len(binary_data):
                        break
                    value = binary_data[offset] != 0
                    offset += 1
                    record[field_name] = value
                elif field_type == 5:  # Record separator
                    if record:
                        records.append(record)
                    break
                else:
                    # Skip unknown type
                    pass
            
            if record and offset >= len(binary_data):
                records.append(record)
                break
    except Exception as e:
        return f"Error parsing TPACK data: {str(e)}"
    
    # Filter records where available is True
    filtered = [r for r in records if r.get('available') is True]
    
    # Format output
    result = []
    for record in filtered:
        result.append(str(record))
    
    return '\n'.join(result) if result else '[]'