def parse_vdl_schema(vdl_content):
    import re
    import json
    
    lines = vdl_content.strip().split('\n')
    result = {'name': '', 'version': 0, 'fields': []}
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Parse header
        if line.startswith('@schema'):
            match = re.match(r'@schema\s+(\w+)\s+@version\s+(\d+)', line)
            if match:
                result['name'] = match.group(1)
                result['version'] = int(match.group(2))
            continue
        
        # Parse field definition
        if ':' in line and not line.startswith('>'):
            # Extract field name and rest
            parts = line.split(':', 1)
            field_name = parts[0].strip()
            
            # Check if array field
            is_array = field_name.startswith('*')
            if is_array:
                field_name = field_name[1:].strip()
            
            rest = parts[1].strip()
            
            # Extract type and flags
            type_match = re.match(r'([A-Z](?:\([^)]*\))?)', rest)
            if not type_match:
                continue
            
            type_code = type_match.group(1)
            flags_str = rest[len(type_code):].strip()
            
            # Parse type
            field_type = ''
            enum_values = []
            if type_code.startswith('E('):
                field_type = 'enum'
                enum_match = re.match(r'E\(([^)]*)\)', type_code)
                if enum_match:
                    enum_values = [v.strip() for v in enum_match.group(1).split('|')]
            elif type_code == 'S':
                field_type = 'string'
            elif type_code == 'I':
                field_type = 'integer'
            elif type_code == 'F':
                field_type = 'float'
            elif type_code == 'B':
                field_type = 'boolean'
            
            # Parse flags
            flags = []
            flag_pattern = r'\[([^\]]+)\]'
            for flag_match in re.finditer(flag_pattern, flags_str):
                flag_content = flag_match.group(1)
                if flag_content == 'R':
                    flags.append('required')
                elif flag_content == 'U':
                    flags.append('unique')
                elif flag_content == 'N':
                    flags.append('nullable')
                elif flag_content.startswith('V('):
                    range_match = re.match(r'V\(([^)]*)\)', flag_content)
                    if range_match:
                        flags.append(f'range({range_match.group(1)})')
            
            # Build field dict
            field_dict = {
                'name': field_name,
                'type': field_type,
                'is_array': is_array,
                'flags': flags
            }
            if enum_values:
                field_dict['values'] = enum_values
            
            result['fields'].append(field_dict)
    
    return json.dumps(result)