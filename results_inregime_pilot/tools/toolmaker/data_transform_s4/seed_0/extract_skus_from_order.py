import json
import traceback

def extract_skus_from_order(order_json_str):
    """
    Extracts all item SKUs from a deserialized TPACK order object.
    
    Args:
        order_json_str: A JSON string representing a single order object
        
    Returns:
        A JSON string representation of a list of SKU strings
    """
    try:
        order = json.loads(order_json_str)
        skus = [item['sku'] for item in order.get('items', [])]
        return json.dumps(skus)
    except Exception as e:
        import sys
        sys.stderr.write(traceback.format_exc())
        raise