def validate_product_records(schema_json, records_json):
    import json
    
    schema = json.loads(schema_json)
    records = json.loads(records_json)
    
    results = []
    valid_count = 0
    invalid_count = 0
    
    for idx, record in enumerate(records):
        errors = []
        
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
            
            if field_type == 'string':
                if not isinstance(value, str):
                    errors.append(f"Field {field_name} must be string, got {type(value).__name__}")
            
            elif field_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field {field_name} must be float, got {type(value).__name__}")
                else:
                    for flag in flags:
                        if flag.startswith('V(') and flag.endswith(')'):
                            range_str = flag[2:-1]
                            parts = range_str.split('..')
                            if len(parts) == 2:
                                try:
                                    min_val = float(parts[0])
                                    max_val = float(parts[1])
                                    if not (min_val <= value <= max_val):
                                        errors.append(f"Field {field_name} value {value} outside range ({min_val}..{max_val})")
                                except ValueError:
                                    pass
            
            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    errors.append(f"Field {field_name} must be boolean, got {type(value).__name__}")
            
            elif field_type == 'enum':
                allowed_values = field.get('values', [])
                if value not in allowed_values:
                    errors.append(f"Field {field_name} value '{value}' not in allowed values: {allowed_values}")
        
        status = "Invalid" if errors else "Valid"
        if errors:
            invalid_count += 1
        else:
            valid_count += 1
        
        results.append({
            'record_index': idx,
            'record': record,
            'status': status,
            'errors': errors
        })
    
    report = f"Validation Results\n"
    report += f"Total Records: {len(records)}\n"
    report += f"Valid Records: {valid_count}\n"
    report += f"Invalid Records: {invalid_count}\n\n"
    
    for result in results:
        report += f"Record {result['record_index']}: {result['status']}\n"
        if result['errors']:
            for error in result['errors']:
                report += f"  - {error}\n"
        report += "\n"
    
    return report