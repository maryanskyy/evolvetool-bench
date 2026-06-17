def extract_skus_from_order(order_json_str):
    """
    Extracts all SKU strings from a deserialized TPACK order object.
    
    Args:
        order_json_str: A JSON string representation of the order object
        
    Returns:
        A comma-separated string of SKUs, or empty string if no items found
    """
    import json
    
    try:
        order = json.loads(order_json_str)
        items = order.get('items', [])
        skus = [item.get('sku') for item in items if 'sku' in item]
        return ','.join(skus)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return ''