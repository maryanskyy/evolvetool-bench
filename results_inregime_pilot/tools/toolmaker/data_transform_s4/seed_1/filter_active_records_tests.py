import json
import sys
from io import StringIO

def filter_active_records(json_data):
    import json
    import traceback
    try:
        records = json.loads(json_data)
        if not isinstance(records, list):
            return json.dumps([])
        filtered = [record for record in records if isinstance(record, dict) and record.get('active') is True]
        return json.dumps(filtered)
    except Exception as e:
        traceback.print_exc()
        return json.dumps([])

def test_filter_active_records_basic():
    """Test filtering with the provided example data."""
    input_data = '[{"name": "Alice", "age": 30, "active": true, "score": 95.5, "role": "admin"}, {"name": "Bob", "age": 25, "active": false, "score": 72.0, "role": "viewer"}, {"name": "Charlie", "age": 35, "active": true, "score": 88.3, "role": "editor"}]'
    result = filter_active_records(input_data)
    parsed = json.loads(result)
    if len(parsed) == 2 and parsed[0]['name'] == 'Alice' and parsed[1]['name'] == 'Charlie':
        print("PASS")
    else:
        print(f"FAIL: Expected 2 records (Alice and Charlie), got {len(parsed)}")

def test_filter_active_records_all_inactive():
    """Test filtering when all records are inactive."""
    input_data = '[{"name": "Dave", "active": false}, {"name": "Eve", "active": false}]'
    result = filter_active_records(input_data)
    parsed = json.loads(result)
    if len(parsed) == 0:
        print("PASS")
    else:
        print(f"FAIL: Expected 0 records, got {len(parsed)}")

def test_filter_active_records_all_active():
    """Test filtering when all records are active."""
    input_data = '[{"name": "Frank", "active": true}, {"name": "Grace", "active": true}]'
    result = filter_active_records(input_data)
    parsed = json.loads(result)
    if len(parsed) == 2 and parsed[0]['name'] == 'Frank' and parsed[1]['name'] == 'Grace':
        print("PASS")
    else:
        print(f"FAIL: Expected 2 records, got {len(parsed)}")

def test_filter_active_records_empty_list():
    """Test filtering with an empty list."""
    input_data = '[]'
    result = filter_active_records(input_data)
    parsed = json.loads(result)
    if len(parsed) == 0:
        print("PASS")
    else:
        print(f"FAIL: Expected 0 records, got {len(parsed)}")

def test_filter_active_records_missing_active_field():
    """Test filtering when some records lack the 'active' field."""
    input_data = '[{"name": "Henry", "active": true}, {"name": "Iris"}]'
    result = filter_active_records(input_data)
    parsed = json.loads(result)
    if len(parsed) == 1 and parsed[0]['name'] == 'Henry':
        print("PASS")
    else:
        print(f"FAIL: Expected 1 record (Henry), got {len(parsed)}")

if __name__ == '__main__':
    test_filter_active_records_basic()
    test_filter_active_records_all_inactive()
    test_filter_active_records_all_active()
    test_filter_active_records_empty_list()
    test_filter_active_records_missing_active_field()