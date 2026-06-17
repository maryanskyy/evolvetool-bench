def validate_records_against_schema(schema_json_str, records_json_str):
    import json
    
    schema = json.loads(schema_json_str)
    records = json.loads(records_json_str)
    
    results = []
    
    for idx, record in enumerate(records, 1):
        record_result = {'record_num': idx, 'status': 'VALID', 'issues': []}
        
        for field in schema['fields']:
            field_name = field['name']
            field_type = field['type']
            flags = field.get('flags', [])
            
            # Check if field is required
            is_required = 'R' in flags
            
            # Get field value
            value = record.get(field_name)
            
            # Check if field is missing and required
            if value is None and is_required:
                record_result['issues'].append(f"Field '{field_name}' is required but missing")
                record_result['status'] = 'INVALID'
                continue
            
            if value is None:
                continue
            
            # Type validation
            type_valid = False
            if field_type == 'string':
                type_valid = isinstance(value, str)
            elif field_type == 'integer':
                type_valid = isinstance(value, int) and not isinstance(value, bool)
            elif field_type == 'float':
                type_valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif field_type == 'enum':
                type_valid = value in field.get('values', [])
            
            if not type_valid:
                record_result['issues'].append(f"Field '{field_name}' has wrong type: expected {field_type}, got {type(value).__name__}")
                record_result['status'] = 'INVALID'
                continue
            
            # Range validation for integers
            if field_type == 'integer':
                for flag in flags:
                    if flag.startswith('V(') and flag.endswith(')'):
                        range_str = flag[2:-1]
                        if '..' in range_str:
                            parts = range_str.split('..')
                            min_val = int(parts[0])
                            max_val = int(parts[1])
                            if not (min_val <= value <= max_val):
                                record_result['issues'].append(f"Field '{field_name}' value {value} is outside valid range [{min_val}..{max_val}]")
                                record_result['status'] = 'INVALID'
            
            # Enum validation
            if field_type == 'enum':
                valid_values = field.get('values', [])
                if value not in valid_values:
                    record_result['issues'].append(f"Field '{field_name}' value '{value}' is not in allowed enum values: {valid_values}")
                    record_result['status'] = 'INVALID'
        
        results.append(record_result)
    
    output = []
    for result in results:
        status_symbol = '✅' if result['status'] == 'VALID' else '❌'
        output.append(f"Record {result['record_num']}: {result['status']} {status_symbol}")
        if result['issues']:
            for issue in result['issues']:
                output.append(f"  - {issue}")
    
    return '\n'.join(output)