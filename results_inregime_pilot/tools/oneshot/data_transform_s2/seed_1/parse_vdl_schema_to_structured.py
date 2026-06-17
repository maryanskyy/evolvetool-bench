def parse_vdl_schema_to_structured(vdl_schema_text):
    import json
    import re
    
    lines = vdl_schema_text.strip().split('\n')
    
    # Parse schema header
    schema_name = None
    schema_version = None
    header_match = re.match(r'@schema\s+(\w+)\s+@version\s+(\d+)', lines[0])
    if header_match:
        schema_name = header_match.group(1)
        schema_version = int(header_match.group(2))
    
    # Parse fields
    fields = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        
        # Parse field definition: name : type [flags]
        field_match = re.match(r'(\w+)\s*:\s*(\w+)(.*)$', line)
        if not field_match:
            continue
        
        field_name = field_match.group(1)
        field_type = field_match.group(2)
        flags_str = field_match.group(3).strip()
        
        # Map type codes to full names
        type_map = {'S': 'String', 'F': 'Float', 'E': 'Enum', 'B': 'Boolean', 'I': 'Integer'}
        full_type = type_map.get(field_type, field_type)
        
        # Parse flags and constraints
        flags = []
        enum_values = []
        validation_range = None
        
        flag_pattern = r'\[([^\]]+)\]'
        for match in re.finditer(flag_pattern, flags_str):
            flag_content = match.group(1)
            if flag_content.startswith('V('):
                # Parse validation range
                range_match = re.match(r'V\((-?\d+)\.\.(-?\d+)\)', flag_content)
                if range_match:
                    validation_range = {'min': int(range_match.group(1)), 'max': int(range_match.group(2))}
            elif flag_content.startswith('E('):
                # Parse enum values
                enum_str = flag_content[2:-1]
                enum_values = [v.strip() for v in enum_str.split('|')]
            else:
                flags.append(flag_content)
        
        # Build field object
        field_obj = {
            'name': field_name,
            'type': full_type,
            'flags': flags,
            'required': 'R' in flags,
            'unique': 'U' in flags
        }
        
        if enum_values:
            field_obj['enum_values'] = enum_values
        if validation_range:
            field_obj['validation_range'] = validation_range
        
        fields.append(field_obj)
    
    # Build result structure
    result = {
        'schema_metadata': {
            'name': schema_name,
            'version': schema_version
        },
        'fields': fields
    }
    
    return json.dumps(result, indent=2)