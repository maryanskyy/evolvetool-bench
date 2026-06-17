def parse_vdl_schema_complete(vdl_schema_text):
    import json
    import re
    
    lines = vdl_schema_text.strip().split('\n')
    result = {
        'name': None,
        'version': None,
        'fields': []
    }
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if line.startswith('@schema'):
            parts = line.split()
            result['name'] = parts[1] if len(parts) > 1 else None
        elif line.startswith('@version'):
            parts = line.split()
            result['version'] = int(parts[1]) if len(parts) > 1 else None
        elif ':' in line:
            field_match = re.match(r'(\w+)\s*:\s*([A-Z])(.*)$', line)
            if field_match:
                field_name = field_match.group(1)
                field_type_code = field_match.group(2)
                flags_str = field_match.group(3).strip()
                
                type_map = {'S': 'string', 'F': 'float', 'B': 'boolean', 'E': 'enum', 'I': 'integer'}
                field_type = type_map.get(field_type_code, 'unknown')
                
                field_obj = {
                    'name': field_name,
                    'type': field_type,
                    'is_array': False,
                    'flags': []
                }
                
                if field_type == 'enum':
                    enum_match = re.search(r'E\(([^)]+)\)', line)
                    if enum_match:
                        field_obj['enum_values'] = [v.strip() for v in enum_match.group(1).split('|')]
                
                if '[R]' in flags_str:
                    field_obj['flags'].append('required')
                if '[U]' in flags_str:
                    field_obj['flags'].append('unique')
                if '[N]' in flags_str:
                    field_obj['flags'].append('nullable')
                if '[A]' in flags_str:
                    field_obj['is_array'] = True
                
                range_match = re.search(r'\[V\(([^)]+)\)\]', flags_str)
                if range_match:
                    range_val = range_match.group(1)
                    field_obj['flags'].append(f'range({range_val})')
                
                result['fields'].append(field_obj)
    
    return json.dumps(result, indent=2)