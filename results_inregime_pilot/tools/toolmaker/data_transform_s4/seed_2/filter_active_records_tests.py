import json
import sys
from io import StringIO

def filter_active_records(records_json):
    import json
    import traceback
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

def test_basic_filtering():
    try:
        input_data = '[{"name": "Alice", "age": 30, "active": true, "score": 95.5, "role": "admin"}, {"name": "Bob", "age": 25, "active": false, "score": 72.0, "role": "viewer"}, {"name": "Charlie", "age": 35, "active": true, "score": 88.3, "role": "editor"}]'
        result = filter_active_records(input_data)
        parsed = json.loads(result)
        assert len(parsed) == 2, f"Expected 2 records, got {len(parsed)}"
        assert parsed[0]['name'] == 'Alice', f"Expected first record to be Alice, got {parsed[0]['name']}"
        assert parsed[1]['name'] == 'Charlie', f"Expected second record to be Charlie, got {parsed[1]['name']}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_all_active():
    try:
        input_data = '[{"name": "Alice", "active": true}, {"name": "Bob", "active": true}]'
        result = filter_active_records(input_data)
        parsed = json.loads(result)
        assert len(parsed) == 2, f"Expected 2 records, got {len(parsed)}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_none_active():
    try:
        input_data = '[{"name": "Alice", "active": false}, {"name": "Bob", "active": false}]'
        result = filter_active_records(input_data)
        parsed = json.loads(result)
        assert len(parsed) == 0, f"Expected 0 records, got {len(parsed)}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_empty_list():
    try:
        input_data = '[]'
        result = filter_active_records(input_data)
        parsed = json.loads(result)
        assert len(parsed) == 0, f"Expected 0 records, got {len(parsed)}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_missing_active_field():
    try:
        input_data = '[{"name": "Alice", "age": 30}, {"name": "Bob", "active": true}]'
        result = filter_active_records(input_data)
        parsed = json.loads(result)
        assert len(parsed) == 1, f"Expected 1 record, got {len(parsed)}"
        assert parsed[0]['name'] == 'Bob', f"Expected Bob, got {parsed[0]['name']}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

if __name__ == '__main__':
    print("Test 1: Basic filtering")
    test_basic_filtering()
    print("Test 2: All active")
    test_all_active()
    print("Test 3: None active")
    test_none_active()
    print("Test 4: Empty list")
    test_empty_list()
    print("Test 5: Missing active field")
    test_missing_active_field()