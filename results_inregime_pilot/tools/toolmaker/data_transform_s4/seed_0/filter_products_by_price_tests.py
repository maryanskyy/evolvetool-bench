import json
import traceback
from io import StringIO
import sys

def filter_products_by_price(products_json, min_price):
    try:
        products = json.loads(products_json)
        filtered = [p for p in products if p.get('price', 0) > min_price]
        return json.dumps(filtered, indent=2)
    except Exception:
        traceback.print_exc()
        return json.dumps([])

def test_basic_filtering():
    """Test basic filtering with price threshold of 10.0"""
    products_json = '[{"sku": "WDG-001", "name": "Widget", "price": 9.99, "qty": 100, "available": true}, {"sku": "GDG-002", "name": "Gadget", "price": 24.99, "qty": 50, "available": true}, {"sku": "GZM-003", "name": "Gizmo", "price": 4.99, "qty": 0, "available": false}, {"sku": "THG-004", "name": "Thingamajig", "price": 149.99, "qty": 12, "available": true}]'
    result = filter_products_by_price(products_json, 10.0)
    result_list = json.loads(result)
    if len(result_list) == 2 and result_list[0]['sku'] == 'GDG-002' and result_list[1]['sku'] == 'THG-004':
        print("PASS")
    else:
        print(f"FAIL: Expected 2 products (Gadget and Thingamajig), got {len(result_list)}")

def test_empty_list():
    """Test with empty product list"""
    products_json = '[]'
    result = filter_products_by_price(products_json, 10.0)
    result_list = json.loads(result)
    if len(result_list) == 0:
        print("PASS")
    else:
        print(f"FAIL: Expected empty list, got {result_list}")

def test_all_products_filtered_out():
    """Test when all products are below threshold"""
    products_json = '[{"sku": "A", "price": 5.0}, {"sku": "B", "price": 3.0}]'
    result = filter_products_by_price(products_json, 10.0)
    result_list = json.loads(result)
    if len(result_list) == 0:
        print("PASS")
    else:
        print(f"FAIL: Expected no products, got {len(result_list)}")

def test_all_products_included():
    """Test when all products are above threshold"""
    products_json = '[{"sku": "A", "price": 15.0}, {"sku": "B", "price": 20.0}]'
    result = filter_products_by_price(products_json, 10.0)
    result_list = json.loads(result)
    if len(result_list) == 2:
        print("PASS")
    else:
        print(f"FAIL: Expected 2 products, got {len(result_list)}")

def test_boundary_condition():
    """Test boundary condition where price equals threshold"""
    products_json = '[{"sku": "A", "price": 10.0}, {"sku": "B", "price": 10.01}]'
    result = filter_products_by_price(products_json, 10.0)
    result_list = json.loads(result)
    if len(result_list) == 1 and result_list[0]['sku'] == 'B':
        print("PASS")
    else:
        print(f"FAIL: Expected only product B (price 10.01), got {result_list}")

if __name__ == '__main__':
    test_basic_filtering()
    test_empty_list()
    test_all_products_filtered_out()
    test_all_products_included()
    test_boundary_condition()