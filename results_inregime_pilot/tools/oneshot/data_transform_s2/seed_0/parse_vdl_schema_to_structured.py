def parse_vdl_schema_to_structured(vdl_schema_text):
    import json
    import re
    
    lines = vdl_schema_text.strip().split('\n')
    
    # Parse schema header
    header_match = re.match(r'@schema\s+(\w+)\s+@version\s+(\d+)', lines[0])
    schema_name = header_match.group(1) if header_match else 'Unknown'
    schema_version = int(header_match.group(2)) if header_match else 0
    
    fields = {}
    
    # Parse field definitions
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        
        # Parse field line: name : type [flags]
        field_match = re.match(r'(\w+)\s*:\s*([A-Z])\s*(.*)', line)
        if not field_match:
            continue
        
        field_name = field_match.group(1)
        field_type_code = field_match.group(2)
        flags_str = field_match.group(3)
        
        # Map type codes to names
        type_map = {'S': 'String', 'F': 'Float', 'I': 'Integer', 'B': 'Boolean', 'E': 'Enum'}
        field_type = type_map.get(field_type_code, 'Unknown')
        
        # Parse flags and constraints
        flags = []
        validation = None
        enum_values = []
        
        flag_pattern = r'\[([^\]]+)\]'
        for match in re.finditer(flag_pattern, flags_str):
            flag_content = match.group(1)
            if flag_content.startswith('V('):
                # Parse validation range
                range_match = re.match(r'V\((-?\d+)\.\.(-?\d+)\)', flag_content)
                if range_match:
                    validation = {'type': 'range', 'min': int(range_match.group(1)), 'max': int(range_match.group(2))}
            elif flag_content.startswith('E('):
                # Parse enum values
                enum_match = re.match(r'E\(([^)]+)\)', flag_content)
                if enum_match:
                    enum_values = [v.strip() for v in enum_match.group(1).split('|')]
            else:
                flags.append(flag_content)
        
        field_def = {
            'name': field_name,
            'type': field_type,
            'flags': flags,
            'required': 'R' in flags,
            'unique': 'U' in flags
        }
        
        if validation:
            field_def['validation'] = validation
        if enum_values:
            field_def['enum_values'] = enum_values
        
        fields[field_name] = field_def
    
    result = {
        'schema_name': schema_name,
        'version': schema_version,
        'fields': fields
    }
    
    return json.dumps(result, indent=2)