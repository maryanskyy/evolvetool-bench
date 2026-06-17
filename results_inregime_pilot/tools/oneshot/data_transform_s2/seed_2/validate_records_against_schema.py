def validate_records_against_schema(schema_json, records_json):
    import json
    
    schema = json.loads(schema_json)
    records = json.loads(records_json)
    
    results = []
    field_map = {f['name']: f for f in schema['fields']}
    
    for idx, record in enumerate(records, 1):
        errors = []
        
        for field_name, field_def in field_map.items():
            if field_name not in record:
                if 'R' in field_def.get('flags', []):
                    errors.append(f"Field '{field_name}' is required but missing")
                continue
            
            value = record[field_name]
            field_type = field_def['type']
            
            # Type validation
            if field_type == 'string':
                if not isinstance(value, str):
                    errors.append(f"Field '{field_name}' must be string, got {type(value).__name__}")
            elif field_type == 'integer':
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"Field '{field_name}' must be integer, got {type(value).__name__}")
            elif field_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field '{field_name}' must be float, got {type(value).__name__}")
            elif field_type == 'enum':
                if value not in field_def.get('values', []):
                    errors.append(f"Field '{field_name}' must be one of {field_def['values']}, got '{value}'")
            
            # Range validation (V flag)
            if not errors or field_name not in [e.split("'")[1] for e in errors if "must be" in e]:
                for flag in field_def.get('flags', []):
                    if flag.startswith('V(') and flag.endswith(')'):
                        range_str = flag[2:-1]
                        if '..' in range_str:
                            min_val, max_val = map(int, range_str.split('..'))
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                if value < min_val or value > max_val:
                                    errors.append(f"Field '{field_name}' value {value} out of range [{min_val}..{max_val}]")
        
        status = "VALID" if not errors else "INVALID"
        results.append({
            'record': idx,
            'status': status,
            'data': record,
            'errors': errors
        })
    
    return json.dumps(results, indent=2)