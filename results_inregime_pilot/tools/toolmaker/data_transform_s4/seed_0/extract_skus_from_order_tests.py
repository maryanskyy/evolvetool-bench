import json
import sys
from io import StringIO

def extract_skus_from_order(order_json_str):
    import traceback
    try:
        order = json.loads(order_json_str)
        skus = [item['sku'] for item in order.get('items', [])]
        return json.dumps(skus)
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        raise

def test_standard_order():
    """Test with a standard order containing multiple items"""
    try:
        order_json = '{"order_id": "ORD-2025-0042", "customer": {"name": "Diana", "email": "diana@test.com"}, "items": [{"sku": "WDG-001", "qty": 3, "unit_price": 9.99}, {"sku": "GDG-002", "qty": 1, "unit_price": 24.99}], "total": 54.96, "shipped": false, "notes": null}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps(['WDG-001', 'GDG-002'])
        assert result == expected, f"Expected {expected}, got {result}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_item_order():
    """Test with an order containing a single item"""
    try:
        order_json = '{"order_id": "ORD-2025-0001", "items": [{"sku": "SKU-123", "qty": 5, "unit_price": 19.99}], "total": 99.95}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps(['SKU-123'])
        assert result == expected, f"Expected {expected}, got {result}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_empty_items_array():
    """Test with an order containing no items"""
    try:
        order_json = '{"order_id": "ORD-2025-0099", "items": [], "total": 0}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps([])
        assert result == expected, f"Expected {expected}, got {result}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_missing_items_key():
    """Test with an order missing the items key entirely"""
    try:
        order_json = '{"order_id": "ORD-2025-0050", "customer": {"name": "John"}, "total": 0}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps([])
        assert result == expected, f"Expected {expected}, got {result}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_multiple_items_with_special_skus():
    """Test with multiple items having special characters in SKUs"""
    try:
        order_json = '{"order_id": "ORD-2025-0100", "items": [{"sku": "SKU-ABC-123", "qty": 2}, {"sku": "SKU_XYZ_789", "qty": 1}, {"sku": "SKU.DEF.456", "qty": 3}], "total": 100}'
        result = extract_skus_from_order(order_json)
        expected = json.dumps(['SKU-ABC-123', 'SKU_XYZ_789', 'SKU.DEF.456'])
        assert result == expected, f"Expected {expected}, got {result}"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {str(e)}")

if __name__ == '__main__':
    test_standard_order()
    test_single_item_order()
    test_empty_items_array()
    test_missing_items_key()
    test_multiple_items_with_special_skus()