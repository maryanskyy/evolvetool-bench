def parse_vdl_schema(schema_text):
    """
    Parse a VDL (Value Definition Language) schema into a structured representation.
    
    Utility:
        Parses VDL schema format into a dictionary containing schema metadata and field definitions.
        Extracts field names, types, array indicators, and constraint flags.
    
    Args:
        schema_text (str): The VDL schema as a multi-line string
    
    Returns:
        dict: A structured representation with 'name', 'version', and 'fields' keys.
              Each field contains name, type, is_array, and flags.
    """
    import re
    
    lines = schema_text.strip().split('\n')
    
    schema = {
        'name': None,
        'version': None,
        'fields': []
    }
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Parse schema header
        if line.startswith('@schema'):
            match = re.match(r'@schema\s+(\w+)\s+@version\s+(\d+)', line)
            if match:
                schema['name'] = match.group(1)
                schema['version'] = int(match.group(2))
            continue
        
        # Parse field definitions
        field_match = re.match(r'(\w+)\s*:\s*(.+)', line)
        if field_match:
            field_name = field_match.group(1)
            field_def = field_match.group(2)
            
            field = {
                'name': field_name,
                'type': None,
                'is_array': False,
                'flags': []
            }
            
            # Extract type and constraints
            tokens = field_def.split()
            
            # First token is the type
            type_token = tokens[0]
            
            # Handle enum types E(...)
            if type_token.startswith('E('):
                field['type'] = 'enum'
                enum_match = re.search(r'E\(([^)]+)\)', type_token)
                if enum_match:
                    field['enum_values'] = enum_match.group(1).split('|')
            else:
                # Map type codes to names
                type_map = {'S': 'string', 'F': 'float', 'B': 'boolean', 'I': 'integer'}
                field['type'] = type_map.get(type_token, type_token)
            
            # Process flags and constraints
            for token in tokens[1:]:
                if token == '[R]':
                    field['flags'].append('required')
                elif token == '[U]':
                    field['flags'].append('unique')
                elif token == '[N]':
                    field['flags'].append('nullable')
                elif token.startswith('[V('):
                    # Extract validation range
                    range_match = re.search(r'\[V\(([^)]+)\)\]', token)
                    if range_match:
                        field['flags'].append(f'range({range_match.group(1)})')
                elif token == '[A]':
                    field['is_array'] = True
            
            schema['fields'].append(field)
    
    return schema