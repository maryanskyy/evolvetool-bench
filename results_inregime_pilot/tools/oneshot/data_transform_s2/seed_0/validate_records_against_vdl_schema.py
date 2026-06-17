def validate_records_against_vdl_schema(schema_json, records_json):
    import json
    
    schema = json.loads(schema_json)
    records = json.loads(records_json)
    
    results = []
    
    for record in records:
        errors = []
        
        # Check each field in the schema
        for field in schema['fields']:
            field_name = field['name']
            field_type = field['type']
            flags = field.get('flags', [])
            is_required = 'R' in flags
            is_nullable = 'N' in flags
            
            # Check if field is present
            if field_name not in record:
                if is_required:
                    errors.append(f"Missing required field: {field_name}")
                continue
            
            value = record[field_name]
            
            # Check if value is None
            if value is None:
                if not is_nullable:
                    errors.append(f"Field {field_name} cannot be null")
                continue
            
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
            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    errors.append(f"Field {field_name} must be boolean, got {type(value).__name__}")
            elif field_type == 'enum':
                allowed_values = field.get('values', [])
                if value not in allowed_values:
                    errors.append(f"Field {field_name} value '{value}' is invalid (must be: {', '.join(allowed_values)})")
            
            # Range validation V(min..max)
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
                                    errors.append(f"Field {field_name} value {value} is outside range ({min_val}..{max_val})")
                        except (ValueError, IndexError):
                            pass
        
        results.append({
            'valid': len(errors) == 0,
            'errors': errors
        })
    
    return json.dumps(results)