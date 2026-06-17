import json
import traceback

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
        import sys
        sys.stderr.write(traceback.format_exc())
        raise