def validate_records_against_schema(schema, records):
    """
    Validate data records against a parsed VDL schema.

    Utility:
        Validates a list of data records against a VDL (Value Definition Language) schema.
        Checks for required fields, type correctness, range constraints, and enum validity.
        Returns detailed validation results for each record.

    Args:
        schema (dict): Parsed VDL schema containing 'name', 'version', and 'fields' list.
                      Each field has 'name', 'type', 'is_array', 'flags', and optional 'values' for enums.
        records (list): List of dictionaries representing data records to validate.

    Returns:
        list: List of validation result dictionaries, each containing:
              - 'valid' (bool): Whether the record passed all validations
              - 'errors' (list): List of error messages describing validation failures
    """
    import re

    results = []
    fields = {field['name']: field for field in schema['fields']}

    for record in records:
        errors = []

        # Check each field in the schema
        for field in schema['fields']:
            field_name = field['name']
            field_type = field['type']
            flags = field.get('flags', [])
            is_required = 'R' in flags
            is_nullable = 'N' in flags

            # Check if field is present in record
            if field_name not in record:
                if is_required:
                    errors.append(f"Missing required field: `{field_name}`")
                continue

            value = record[field_name]

            # Check if value is None
            if value is None:
                if not is_nullable:
                    errors.append(f"Field `{field_name}` cannot be None (not nullable)")
                continue

            # Type validation
            if field_type == 'string':
                if not isinstance(value, str):
                    errors.append(f"Field `{field_name}` must be string, got {type(value).__name__}")

            elif field_type == 'integer':
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"Field `{field_name}` must be integer, got {type(value).__name__}")
                else:
                    # Check range constraints V(min..max)
                    for flag in flags:
                        if flag.startswith('V(') and flag.endswith(')'):
                            range_str = flag[2:-1]
                            if '..' in range_str:
                                min_str, max_str = range_str.split('..')
                                try:
                                    min_val = int(min_str)
                                    max_val = int(max_str)
                                    if value < min_val or value > max_val:
                                        errors.append(f"Field `{field_name}` value {value} is outside range [{min_val}..{max_val}]")
                                except ValueError:
                                    pass

            elif field_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field `{field_name}` must be float, got {type(value).__name__}")
                else:
                    # Check range constraints V(min..max)
                    for flag in flags:
                        if flag.startswith('V(') and flag.endswith(')'):
                            range_str = flag[2:-1]
                            if '..' in range_str:
                                min_str, max_str = range_str.split('..')
                                try:
                                    min_val = float(min_str)
                                    max_val = float(max_str)
                                    if value < min_val or value > max_val:
                                        errors.append(f"Field `{field_name}` value {value} is outside range [{min_val}..{max_val}]")
                                except ValueError:
                                    pass

            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    errors.append(f"Field `{field_name}` must be boolean, got {type(value).__name__}")

            elif field_type == 'enum':
                allowed_values = field.get('values', [])
                if value not in allowed_values:
                    errors.append(f"Field `{field_name}` value '{value}' is not in allowed enum values {allowed_values}")

        # Check for extra fields not in schema
        for field_name in record:
            if field_name not in fields:
                errors.append(f"Unknown field: `{field_name}`")

        results.append({
            'valid': len(errors) == 0,
            'errors': errors
        })

    return results