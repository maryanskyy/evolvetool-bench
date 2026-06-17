def validate_edge_case_records(schema_json, records_json):
    import json
    
    schema = json.loads(schema_json)
    records = json.loads(records_json)
    
    results = []
    valid_count = 0
    invalid_count = 0
    
    # Build field metadata from schema
    field_map = {}
    for field in schema.get('fields', []):
        field_map[field['name']] = field
    
    for idx, record in enumerate(records, 1):
        errors = []
        
        # Check each field in schema
        for field in schema.get('fields', []):
            field_name = field['name']
            field_type = field['type']
            flags = field.get('flags', [])
            is_required = 'R' in flags
            
            # Check if field exists and is required
            if field_name not in record:
                if is_required:
                    errors.append(f"Required field '{field_name}' is missing")
                continue
            
            value = record[field_name]
            
            # Type validation
            if field_type == 'string':
                if not isinstance(value, str):
                    errors.append(f"Field {field_name} must be string, got {type(value).__name__}")
            elif field_type == 'integer':
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"Field {field_name} must be integer, got {type(value).__name__}")
            elif field_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field {field_name} must be float, got {type(value).__name__}")
            elif field_type == 'enum':
                valid_values = field.get('values', [])
                if value not in valid_values:
                    errors.append(f"Field {field_name} must be one of {valid_values}, got {value}")
            
            # Range validation for integers with V flag
            if field_type == 'integer' and isinstance(value, int):
                for flag in flags:
                    if flag.startswith('V(') and flag.endswith(')'):
                        range_str = flag[2:-1]
                        if '..' in range_str:
                            parts = range_str.split('..')
                            min_val = int(parts[0])
                            max_val = int(parts[1])
                            if value < min_val or value > max_val:
                                errors.append(f"Field {field_name} value {value} out of range [{min_val}..{max_val}]")
        
        if errors:
            invalid_count += 1
            results.append(f"Record {idx}: INVALID - {'; '.join(errors)}")
        else:
            valid_count += 1
            results.append(f"Record {idx}: VALID")
    
    summary = f"Total: {len(records)}, Valid: {valid_count}, Invalid: {invalid_count}\n"
    return summary + "\n".join(results)