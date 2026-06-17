def filter_records_by_boolean_field(records_json, field_name, field_value):
    """
    Filters deserialized records by a boolean field value.
    
    Args:
        records_json: JSON string representation of list of record dictionaries
        field_name: Name of the boolean field to filter on (str)
        field_value: Boolean value to match (str: 'true' or 'false')
    
    Returns:
        JSON string containing filtered records
    """
    import json
    
    # Parse input JSON
    records = json.loads(records_json)
    
    # Convert string boolean to actual boolean
    target_value = field_value.lower() == 'true'
    
    # Filter records where the specified field matches the target value
    filtered = [record for record in records if record.get(field_name) == target_value]
    
    # Return as JSON string
    return json.dumps(filtered, indent=2)