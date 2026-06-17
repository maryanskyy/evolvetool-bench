import json
import sys
from io import StringIO

def extract_skus_from_order(order_json_str):
    import traceback
    try:
        order = json.loads(order_json_str)
        
        if not isinstance(order, dict):
            raise ValueError("Order must be a dictionary object")
        
        if 'items' not in order:
            raise ValueError("Order must contain 'items' key")
        
        items = order['items']
        if not isinstance(items, list):
            raise ValueError("'items' must be a list")
        
        skus = []
        for item in items:
            if isinstance(item, dict) and 'sku' in item:
                skus.append(item['sku'])
        
        return json.dumps(skus)
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        raise

def test_basic_order():
    order_json = '{"order_id": "ORD-2025-0042", "customer": {"name": "Diana", "email": "diana@test.com"}, "items": [{"sku": "WDG-001", "qty": 3, "unit_price": 9.99}, {"sku": "GDG-002", "qty": 1, "unit_price": 24.99}], "total": 54.96, "shipped": false, "notes": null}'
    result = extract_skus_from_order(order_json)
    expected = json.dumps(['WDG-001', 'GDG-002'])
    if result == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {result}")

def test_single_item():
    order_json = '{"order_id": "ORD-2025-0001", "items": [{"sku": "SKU-123", "qty": 1}]}'
    result = extract_skus_from_order(order_json)
    expected = json.dumps(['SKU-123'])
    if result == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {result}")

def test_empty_items():
    order_json = '{"order_id": "ORD-2025-0002", "items": []}'
    result = extract_skus_from_order(order_json)
    expected = json.dumps([])
    if result == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {result}")

def test_multiple_items():
    order_json = '{"order_id": "ORD-2025-0003", "items": [{"sku": "A-001", "qty": 2}, {"sku": "B-002", "qty": 1}, {"sku": "C-003", "qty": 5}]}'
    result = extract_skus_from_order(order_json)
    expected = json.dumps(['A-001', 'B-002', 'C-003'])
    if result == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {result}")

def test_missing_items_key():
    order_json = '{"order_id": "ORD-2025-0004", "customer": {"name": "John"}}'
    try:
        result = extract_skus_from_order(order_json)
        print("FAIL: Should have raised ValueError for missing 'items' key")
    except ValueError as e:
        if "'items'" in str(e):
            print("PASS")
        else:
            print(f"FAIL: Wrong error message: {e}")
    except Exception as e:
        print(f"FAIL: Unexpected exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_basic_order()
    test_single_item()
    test_empty_items()
    test_multiple_items()
    test_missing_items_key()