def extract_skus_from_order(order_json_str):
    import json
    order = json.loads(order_json_str)
    skus = [item['sku'] for item in order.get('items', [])]
    return json.dumps(skus)