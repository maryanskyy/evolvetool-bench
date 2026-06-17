import json
import sys
from io import StringIO

def extract_skus_from_order(order_json_str):
    """
    Extracts all item SKUs from a deserialized TPACK order object.
    
    Args:
        order_json_str: A JSON string representing a single order object
        
    Returns:
        A JSON string containing a list of SKU strings
    """
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
        import traceback
        sys.stderr.write(traceback.format_exc())
        raise


def test_standard_order():
    """Test with the provided standard order data."""
    try:
        order_json = '{"order_id": "ORD-2025-0042", "customer": {"name": "Diana", "email": "diana@test.com"}, "items": [{"sku": "WDG-001", "qty": 3, "unit_price": 9.99}, {"sku": "GDG-002", "qty": 1, "unit_price": 24.99}], "total": 54.96, "shipped": false, "notes": null}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps(['WDG-001', 'GDG-002'])
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")


def test_single_item_order():
    """Test with an order containing a single item."""
    try:
        order_json = '{"order_id": "ORD-2025-0001", "items": [{"sku": "SKU-123", "qty": 5}]}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps(['SKU-123'])
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")


def test_empty_items_array():
    """Test with an order containing an empty items array."""
    try:
        order_json = '{"order_id": "ORD-2025-0003", "items": []}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps([])
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")


def test_multiple_items():
    """Test with an order containing multiple items."""
    try:
        order_json = '{"order_id": "ORD-2025-0004", "items": [{"sku": "A-001", "qty": 1}, {"sku": "B-002", "qty": 2}, {"sku": "C-003", "qty": 3}, {"sku": "D-004", "qty": 4}]}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps(['A-001', 'B-002', 'C-003', 'D-004'])
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")


def test_missing_items_key():
    """Test with an order missing the items key."""
    try:
        order_json = '{"order_id": "ORD-2025-0005", "customer": {"name": "John"}}'
        result = extract_skus_from_order(order_json)
        print(f"FAIL: Should have raised ValueError but got {result}")
    except ValueError as e:
        if "items" in str(e):
            print("PASS")
        else:
            print(f"FAIL: Wrong error message: {str(e)}")
    except Exception as e:
        print(f"FAIL: Wrong exception type: {type(e).__name__}")


if __name__ == "__main__":
    test_standard_order()
    test_single_item_order()
    test_empty_items_array()
    test_multiple_items()
    test_missing_items_key()