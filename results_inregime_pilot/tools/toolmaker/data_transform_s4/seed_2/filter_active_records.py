import json
import traceback

def filter_active_records(records_json):
    """
    Filters user records to return only those where 'active' is True.
    
    Args:
        records_json (str): A JSON string representing a list of user record dictionaries.
    
    Returns:
        str: A JSON string containing only the records where 'active' is True.
    """
    try:
        records = json.loads(records_json)
        if not isinstance(records, list):
            raise ValueError("Input must be a JSON array of records")
        
        filtered = [record for record in records if isinstance(record, dict) and record.get('active') is True]
        return json.dumps(filtered, indent=2)
    except Exception as e:
        import sys
        traceback.print_exc(file=sys.stderr)
        raise