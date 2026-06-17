def deserialize_and_filter_tpack(tpack_base64_data: str) -> str:
    import base64
    import struct
    
    try:
        # Decode base64
        binary_data = base64.b64decode(tpack_base64_data)
        
        records = []
        offset = 0
        
        while offset < len(binary_data):
            record = {}
            
            # Parse each field in the record
            while offset < len(binary_data):
                # Read field type byte
                field_type = binary_data[offset]
                offset += 1
                
                # Read field name length and name
                name_len = binary_data[offset]
                offset += 1
                field_name = binary_data[offset:offset + name_len].decode('utf-8')
                offset += name_len
                
                # Parse value based on type
                if field_type == 3:  # String type
                    value_len = binary_data[offset]
                    offset += 1
                    value = binary_data[offset:offset + value_len].decode('utf-8')
                    offset += value_len
                    record[field_name] = value
                elif field_type == 19:  # Float type
                    value = struct.unpack('>f', binary_data[offset:offset + 4])[0]
                    offset += 4
                    record[field_name] = value
                elif field_type == 16:  # Integer type
                    value = struct.unpack('>I', binary_data[offset:offset + 4])[0]
                    offset += 4
                    record[field_name] = value
                elif field_type == 2:  # Boolean type
                    value = binary_data[offset] != 0
                    offset += 1
                    record[field_name] = value
                elif field_type == 9:  # End of record marker
                    offset += 1
                    break
                else:
                    offset += 1
            
            if record:
                records.append(record)
        
        # Filter records where available is True
        filtered = [r for r in records if r.get('available') is True]
        
        # Format output as JSON string
        import json
        return json.dumps(filtered, indent=2)
    
    except Exception as e:
        return f'Error: {str(e)}'