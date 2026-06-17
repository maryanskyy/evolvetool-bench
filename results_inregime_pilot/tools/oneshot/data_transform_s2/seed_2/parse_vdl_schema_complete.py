def parse_vdl_schema_complete(vdl_schema_text):
    import json
    import re
    
    lines = vdl_schema_text.strip().split('\n')
    schema_name = None
    version = None
    fields = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if line.startswith('@schema'):
            parts = line.split()
            schema_name = parts[1] if len(parts) > 1 else None
            continue
        
        if line.startswith('@version'):
            parts = line.split()
            version = int(parts[1]) if len(parts) > 1 else None
            continue
        
        if ':' in line:
            field_match = re.match(r'(\w+)\s*:\s*(.+)', line)
            if field_match:
                field_name = field_match.group(1)
                field_def = field_match.group(2)
                
                field_obj = {'name': field_name}
                flags = []
                type_str = None
                constraints = []
                
                tokens = re.findall(r'\w+|\([^)]*\)|\[[^\]]*\]', field_def)
                
                for token in tokens:
                    if token.startswith('[') and token.endswith(']'):
                        flag_content = token[1:-1]
                        if flag_content == 'R':
                            flags.append('required')
                        elif flag_content == 'U':
                            flags.append('unique')
                        elif flag_content == 'N':
                            flags.append('nullable')
                        elif flag_content.startswith('V'):
                            range_match = re.search(r'V\(([^)]+)\)', flag_content)
                            if range_match:
                                constraints.append(f'range({range_match.group(1)})')
                    elif token.startswith('(') and token.endswith(')'):
                        enum_values = token[1:-1].split('|')
                        field_obj['type'] = 'enum'
                        field_obj['enum_values'] = enum_values
                    elif token in ['S', 'F', 'B', 'I', 'E']:
                        type_map = {'S': 'string', 'F': 'float', 'B': 'boolean', 'I': 'integer', 'E': 'enum'}
                        type_str = type_map.get(token, token)
                
                if type_str and 'type' not in field_obj:
                    field_obj['type'] = type_str
                
                field_obj['is_array'] = False
                if flags:
                    field_obj['flags'] = flags
                if constraints:
                    field_obj['constraints'] = constraints
                
                fields.append(field_obj)
    
    result = {
        'name': schema_name,
        'version': version,
        'fields': fields
    }
    
    return json.dumps(result, indent=2)