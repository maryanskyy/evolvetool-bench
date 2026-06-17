def filter_products_by_price(products_json: str, min_price: float) -> str:
    import json
    products = json.loads(products_json)
    filtered = [p for p in products if p.get('price', 0) > min_price]
    return json.dumps(filtered, indent=2)