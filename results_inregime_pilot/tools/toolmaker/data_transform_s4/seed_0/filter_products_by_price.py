import json
import traceback

def filter_products_by_price(products_json, min_price):
    """
    Filters product records to only those with price > min_price.
    
    Args:
        products_json: JSON string containing list of product records
        min_price: Minimum price threshold (float)
    
    Returns:
        JSON string containing filtered product records
    """
    try:
        products = json.loads(products_json)
        filtered = [p for p in products if p.get('price', 0) > min_price]
        return json.dumps(filtered, indent=2)
    except Exception:
        traceback.print_exc()
        return json.dumps([])