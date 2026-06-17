def filter_records_by_field(records, field_name, field_value):
    """
    Filter a list of deserialized data records by a specific field value.
    
    Utility:
        Queries and filters a list of dictionary records to return only those
        where a specified field matches a given value. Useful for extracting
        subsets of data based on criteria.
    
    Args:
        records (list): A list of dictionaries representing data records.
        field_name (str): The key/field name to filter on.
        field_value: The value to match for the specified field.
    
    Returns:
        list: A list of dictionaries containing only records where the
              specified field matches the given value.
    """
    return [record for record in records if record.get(field_name) == field_value]


# Example usage with the provided data
if __name__ == "__main__":
    user_records = [
        {'name': 'Alice', 'age': 30, 'active': True, 'score': 95.5, 'role': 'admin'},
        {'name': 'Bob', 'age': 25, 'active': False, 'score': 72.0, 'role': 'viewer'},
        {'name': 'Charlie', 'age': 35, 'active': True, 'score': 88.3, 'role': 'editor'}
    ]
    
    filtered_results = filter_records_by_field(user_records, 'active', True)
    print(filtered_results)