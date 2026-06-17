import json
import traceback

def filter_active_records(json_data):
    """
    Filters a JSON-serialized list of user records to return only those where 'active' is True.
    
    Args:
        json_data (str): A JSON string representing a list of user record dictionaries.
    
    Returns:
        str: A JSON string containing only the records where 'active' is True.
    """
    try:
        records = json.loads(json_data)
        if not isinstance(records, list):
            return json.dumps([])
        filtered = [record for record in records if isinstance(record, dict) and record.get('active') is True]
        return json.dumps(filtered)
    except Exception as e:
        traceback.print_exc()
        return json.dumps([])