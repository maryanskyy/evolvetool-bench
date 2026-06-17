def validate_records_against_schema(schema, records):
    """
    Validate data records against a parsed VDL schema.

    Utility:
        Validates a list of data records against a VDL (Value Definition Language) schema.
        Checks for required fields, type correctness, range constraints, and enum validity.
        Returns detailed validation results for each record.

    Args:
        schema (dict): Parsed VDL schema containing 'name', 'version', and 'fields' list.
                      Each field has 'name', 'type', 'is_array', 'flags', and optional 'values'.
        records (list): List of dictionaries representing data records to validate.

    Returns:
        list: List of validation result dictionaries, each containing:
              - 'valid' (bool): Whether the record passed all validations
              - 'errors' (list): List of error messages (empty if valid)
    """
    import re

    results = []
    fields = schema.get('fields', [])

    # Create a field lookup dictionary for easier access
    field_map = {field['name']: field for field in fields}

    for record in records:
        errors = []

        # Check each field in the schema
        for field in fields:
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
                            range_str = flag[2:-1]  # Extract "0..150" from "V(0..150)"
                            parts = range_str.split('..')
                            if len(parts) == 2:
                                try:
                                    min_val = int(parts[0])
                                    max_val = int(parts[1])
                                    if value < min_val or value > max_val:
                                        errors.append(f"Field `{field_name}` value {value} is outside range [{min_val}..{max_val}]")
                                except ValueError:
                                    pass

            elif field_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field `{field_name}` must be float, got {type(value).__name__}")
                else:
                    # Check range constraints for float
                    for flag in flags:
                        if flag.startswith('V(') and flag.endswith(')'):
                            range_str = flag[2:-1]
                            parts = range_str.split('..')
                            if len(parts) == 2:
                                try:
                                    min_val = float(parts[0])
                                    max_val = float(parts[1])
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

        # Add result for this record
        results.append({
            'valid': len(errors) == 0,
            'errors': errors
        })

    return results