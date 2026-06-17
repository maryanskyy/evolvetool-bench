def extract_skus_from_order(order_json_str):
    """
    Extracts all item SKUs from a deserialized TPACK order object.
    
    Args:
        order_json_str: A JSON string representation of the order object
        
    Returns:
        A comma-separated string of SKUs, or empty string if no items found
    """
    import json
    
    try:
        order = json.loads(order_json_str)
        skus = []
        
        if 'items' in order and isinstance(order['items'], list):
            for item in order['items']:
                if isinstance(item, dict) and 'sku' in item:
                    skus.append(str(item['sku']))
        
        return ','.join(skus)
    except (json.JSONDecodeError, TypeError, KeyError):
        return ''