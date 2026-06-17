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
            field = parse_vdl_field(line)
            if field:
                result['fields'].append(field)
    
    return json.dumps(result, indent=2)

def parse_vdl_field(field_line):
    import re
    
    parts = field_line.split(':')
    if len(parts) < 2:
        return None
    
    field_name = parts[0].strip()
    rest = parts[1].strip()
    
    field = {'name': field_name, 'type': None, 'is_array': False, 'flags': []}
    
    type_match = re.match(r'^([A-Z])(?:\(([^)]+)\))?', rest)
    if type_match:
        type_char = type_match.group(1)
        enum_values = type_match.group(2)
        
        type_map = {'S': 'string', 'F': 'float', 'B': 'boolean', 'I': 'integer', 'E': 'enum'}
        field['type'] = type_map.get(type_char, 'unknown')
        
        if enum_values:
            field['enum_values'] = [v.strip() for v in enum_values.split('|')]
        
        rest = rest[type_match.end():].strip()
    
    flags = re.findall(r'\[([^\]]+)\]', rest)
    for flag in flags:
        flag = flag.strip()
        if flag == 'R':
            field['flags'].append('required')
        elif flag == 'U':
            field['flags'].append('unique')
        elif flag == 'N':
            field['flags'].append('nullable')
        elif flag.startswith('V('):
            range_match = re.search(r'V\(([^)]+)\)', flag)
            if range_match:
                field['flags'].append(f'range({range_match.group(1)})')
        else:
            field['flags'].append(flag)
    
    return field