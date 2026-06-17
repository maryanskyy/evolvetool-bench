import json
import traceback

def filter_products_by_price(products_json, min_price):
    """
    Filters product records to only those with price > min_price.
    
    Args:
        products_json (str): JSON string containing list of product records
        min_price (float): Minimum price threshold (exclusive)
    
    Returns:
        str: JSON string containing filtered product records
    """
    try:
        products = json.loads(products_json)
        filtered = [p for p in products if p.get('price', 0) > min_price]
        return json.dumps(filtered, indent=2)
    except Exception as e:
        import sys
        traceback.print_exc(file=sys.stderr)
        return json.dumps([])