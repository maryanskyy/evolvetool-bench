def format_vdl_schema_output(schema_name, schema_version, fields_json):
    """
    Formats a parsed VDL schema into a structured markdown representation.
    
    Args:
        schema_name: Name of the schema (e.g., 'Sensor')
        schema_version: Version number as string (e.g., '3')
        fields_json: JSON string containing parsed fields with their properties
    
    Returns:
        Formatted markdown string with schema metadata and field details
    """
    import json
    
    try:
        fields = json.loads(fields_json)
    except (json.JSONDecodeError, TypeError):
        fields = []
    
    output = []
    output.append(f"**Schema Metadata:**")
    output.append(f"- **Name:** {schema_name}")
    output.append(f"- **Version:** {schema_version}")
    output.append("")
    output.append("**Fields:**")
    output.append("")
    
    for idx, field in enumerate(fields, 1):
        field_name = field.get('name', 'unknown')
        field_type = field.get('type', 'unknown')
        flags = field.get('flags', [])
        constraints = field.get('constraints', [])
        
        type_display = field_type.capitalize()
        if field_type == 'enum':
            values = field.get('values', [])
            type_display = f"Enum with values: {', '.join(values)}"
        elif field_type == 'float' and constraints:
            type_display = "Float"
        
        output.append(f"{idx}. **{field_name}** ({type_display})")
        output.append(f"   - Type: `{field_type}`")
        
        if flags:
            flags_str = ', '.join([f"`{f}`" for f in flags])
            output.append(f"   - Flags: {flags_str}")
        else:
            output.append(f"   - Flags: None (optional field)")
        
        if constraints:
            constraint_text = "; ".join(constraints)
            output.append(f"   - Constraints: {constraint_text}")
        
        output.append("")
    
    return "\n".join(output)