def validate_product_records_against_schema(schema_json_str, records_json_str):
    import json
    import re
    
    schema = json.loads(schema_json_str)
    records = json.loads(records_json_str)
    
    # Build field lookup
    fields_by_name = {}
    for field in schema['fields']:
        fields_by_name[field['name']] = field
    
    results = []
    valid_count = 0
    invalid_count = 0
    
    for idx, record in enumerate(records):
        errors = []
        
        # Check each field in schema
        for field in schema['fields']:
            field_name = field['name']
            field_type = field['type']
            flags = field.get('flags', [])
            is_required = 'R' in flags
            
            if field_name not in record:
                if is_required:
                    errors.append(f"Missing required field: {field_name}")
                continue
            
            value = record[field_name]
            
            # Type validation
            if field_type == 'string':
                if not isinstance(value, str):
                    errors.append(f"Field {field_name} must be string, got {type(value).__name__}")
            elif field_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field {field_name} must be float, got {type(value).__name__}")
            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    errors.append(f"Field {field_name} must be boolean, got {type(value).__name__}")
            elif field_type == 'enum':
                allowed_values = field.get('values', [])
                if value not in allowed_values:
                    errors.append(f"Field {field_name} value '{value}' not in allowed values: {allowed_values}")
            
            # Range validation
            for flag in flags:
                if flag.startswith('V(') and flag.endswith(')'):
                    range_str = flag[2:-1]
                    if '..' in range_str:
                        parts = range_str.split('..')
                        try:
                            min_val = float(parts[0])
                            max_val = float(parts[1])
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                if value < min_val or value > max_val:
                                    errors.append(f"Field {field_name} value {value} is outside allowed range ({min_val}..{max_val})")
                        except (ValueError, IndexError):
                            pass
        
        # Check for extra fields not in schema
        for key in record:
            if key not in fields_by_name:
                errors.append(f"Unknown field: {key}")
        
        if errors:
            invalid_count += 1
            results.append(f"Record {idx + 1}: INVALID - {'; '.join(errors)}")
        else:
            valid_count += 1
            results.append(f"Record {idx + 1}: VALID")
    
    summary = f"\nValidation Summary: {valid_count} valid, {invalid_count} invalid out of {len(records)} records"
    return "\n".join(results) + summary