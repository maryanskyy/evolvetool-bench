def parse_vdl_schema(schema_text):
    """
    Parse a VDL (Value Definition Language) schema into a structured representation.
    
    Utility:
        Parses VDL schema definitions and converts them into a structured dictionary
        format that can be easily processed or serialized to JSON. Handles field types,
        array notation, flags (required, unique, nullable), and validation constraints.
    
    Args:
        schema_text (str): The VDL schema as a multi-line string containing schema
                          definition with @schema, @version, and field declarations.
    
    Returns:
        dict: A structured representation containing:
            - name: schema name
            - version: schema version number
            - fields: list of field dictionaries with name, type, is_array, and flags
    """
    import re
    
    lines = schema_text.strip().split('\n')
    result = {
        'name': None,
        'version': None,
        'fields': []
    }
    
    # Parse schema header
    for line in lines:
        schema_match = re.match(r'@schema\s+(\w+)', line)
        if schema_match:
            result['name'] = schema_match.group(1)
        
        version_match = re.match(r'@version\s+(\d+)', line)
        if version_match:
            result['version'] = int(version_match.group(1))
    
    # Parse fields
    for line in lines:
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('@'):
            continue
        
        # Parse field definition: name : type [flags]
        field_match = re.match(r'(\w+)\s*:\s*(.+)', line)
        if not field_match:
            continue
        
        field_name = field_match.group(1)
        field_def = field_match.group(2)
        
        # Extract type and flags
        type_match = re.match(r'([A-Z])\(?([^)]*)\)?\s*(.*)', field_def)
        if not type_match:
            continue
        
        type_code = type_match.group(1)
        type_params = type_match.group(2)
        flags_str = type_match.group(3)
        
        # Map type codes to type names
        type_map = {
            'S': 'string',
            'F': 'float',
            'I': 'integer',
            'B': 'boolean',
            'E': 'enum'
        }
        
        field_type = type_map.get(type_code, 'unknown')
        
        # Handle enum values
        enum_values = []
        if type_code == 'E' and type_params:
            enum_values = [v.strip() for v in type_params.split('|')]
        
        # Parse flags
        flags = []
        is_array = False
        
        flag_pattern = r'\[([^\]]+)\]'
        for flag_match in re.finditer(flag_pattern, flags_str):
            flag_content = flag_match.group(1)
            
            if flag_content == 'R':
                flags.append('required')
            elif flag_content == 'U':
                flags.append('unique')
            elif flag_content == 'N':
                flags.append('nullable')
            elif flag_content == 'A':
                is_array = True
            elif flag_content.startswith('V('):
                # Extract validation range
                range_match = re.match(r'V\(([^)]+)\)', flag_content)
                if range_match:
                    flags.append(f'range({range_match.group(1)})')
        
        field = {
            'name': field_name,
            'type': field_type,
            'is_array': is_array,
            'flags': flags
        }
        
        if enum_values:
            field['enum_values'] = enum_values
        
        result['fields'].append(field)
    
    return result