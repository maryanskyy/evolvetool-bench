def filter_products_by_price(products, min_price):
    """
    Filter product records to only those with price greater than a specified minimum.
    
    Utility:
        Filters a list of product dictionaries based on a price threshold,
        returning only products with price > min_price.
    
    Args:
        products (list): List of product dictionaries, each containing at minimum
                        a 'price' key with a numeric value.
        min_price (float): The minimum price threshold. Products with price > this
                          value will be included in the result.
    
    Returns:
        list: A list of product dictionaries that have price > min_price,
              maintaining the original structure and order of matching records.
    """
    return [product for product in products if product.get('price', 0) > min_price]


# Example usage with the provided data
if __name__ == "__main__":
    products = [
        {'sku': 'WDG-001', 'name': 'Widget', 'price': 9.99, 'qty': 100, 'available': True},
        {'sku': 'GDG-002', 'name': 'Gadget', 'price': 24.99, 'qty': 50, 'available': True},
        {'sku': 'GZM-003', 'name': 'Gizmo', 'price': 4.99, 'qty': 0, 'available': False},
        {'sku': 'THG-004', 'name': 'Thingamajig', 'price': 149.99, 'qty': 12, 'available': True}
    ]
    
    result = filter_products_by_price(products, 10.0)
    print(result)