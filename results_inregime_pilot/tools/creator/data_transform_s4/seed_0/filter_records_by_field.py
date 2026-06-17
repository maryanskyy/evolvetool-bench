def filter_records_by_field(records, field_name, field_value):
    """
    Filter a list of deserialized data records by a specific field value.
    
    Utility:
        Query and filter records from deserialized data structures (like JSON)
        based on matching a specific field to a given value. Useful for
        extracting subsets of data that meet certain criteria.
    
    Args:
        records (list): A list of dictionaries representing data records.
        field_name (str): The name of the field/key to filter on.
        field_value: The value to match against (can be str, int, float, bool, etc).
    
    Returns:
        list: A list of dictionaries containing only records where the specified
              field matches the given value. Returns an empty list if no matches found.
    
    Example:
        >>> users = [
        ...     {'name': 'Alice', 'age': 30, 'active': True, 'score': 95.5, 'role': 'admin'},
        ...     {'name': 'Bob', 'age': 25, 'active': False, 'score': 72.0, 'role': 'viewer'},
        ...     {'name': 'Charlie', 'age': 35, 'active': True, 'score': 88.3, 'role': 'editor'}
        ... ]
        >>> filter_records_by_field(users, 'active', True)
        [{'name': 'Alice', 'age': 30, 'active': True, 'score': 95.5, 'role': 'admin'},
         {'name': 'Charlie', 'age': 35, 'active': True, 'score': 88.3, 'role': 'editor'}]
    """
    return [record for record in records if record.get(field_name) == field_value]