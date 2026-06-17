import json
import sys
from io import StringIO

def filter_products_by_price(products_json, min_price):
    try:
        products = json.loads(products_json)
        filtered = [p for p in products if p.get('price', 0) > min_price]
        return json.dumps(filtered, indent=2)
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return json.dumps([])

def test_basic_filtering():
    products = [
        {'sku': 'WDG-001', 'name': 'Widget', 'price': 9.99, 'qty': 100, 'available': True},
        {'sku': 'GDG-002', 'name': 'Gadget', 'price': 24.99, 'qty': 50, 'available': True},
        {'sku': 'GZM-003', 'name': 'Gizmo', 'price': 4.99, 'qty': 0, 'available': False},
        {'sku': 'THG-004', 'name': 'Thingamajig', 'price': 149.99, 'qty': 12, 'available': True}
    ]
    result = filter_products_by_price(json.dumps(products), 10.0)
    result_list = json.loads(result)
    if len(result_list) == 2 and result_list[0]['sku'] == 'GDG-002' and result_list[1]['sku'] == 'THG-004':
        print("PASS")
    else:
        print(f"FAIL: Expected 2 products (GDG-002, THG-004), got {len(result_list)} products")

def test_empty_list():
    result = filter_products_by_price(json.dumps([]), 10.0)
    result_list = json.loads(result)
    if len(result_list) == 0:
        print("PASS")
    else:
        print(f"FAIL: Expected empty list, got {len(result_list)} products")

def test_all_excluded():
    products = [
        {'sku': 'A', 'price': 5.0},
        {'sku': 'B', 'price': 8.0},
        {'sku': 'C', 'price': 10.0}
    ]
    result = filter_products_by_price(json.dumps(products), 10.0)
    result_list = json.loads(result)
    if len(result_list) == 0:
        print("PASS")
    else:
        print(f"FAIL: Expected 0 products (all prices <= 10.0), got {len(result_list)}")

def test_all_included():
    products = [
        {'sku': 'A', 'price': 10.01},
        {'sku': 'B', 'price': 20.0},
        {'sku': 'C', 'price': 100.0}
    ]
    result = filter_products_by_price(json.dumps(products), 10.0)
    result_list = json.loads(result)
    if len(result_list) == 3:
        print("PASS")
    else:
        print(f"FAIL: Expected 3 products (all prices > 10.0), got {len(result_list)}")

def test_boundary_condition():
    products = [
        {'sku': 'A', 'price': 10.0},
        {'sku': 'B', 'price': 10.001},
        {'sku': 'C', 'price': 9.999}
    ]
    result = filter_products_by_price(json.dumps(products), 10.0)
    result_list = json.loads(result)
    if len(result_list) == 1 and result_list[0]['sku'] == 'B':
        print("PASS")
    else:
        print(f"FAIL: Expected 1 product (B with price 10.001), got {len(result_list)} products")

if __name__ == '__main__':
    test_basic_filtering()
    test_empty_list()
    test_all_excluded()
    test_all_included()
    test_boundary_condition()