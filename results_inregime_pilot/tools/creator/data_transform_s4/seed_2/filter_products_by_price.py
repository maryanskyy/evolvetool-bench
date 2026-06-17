def filter_products_by_price(products, min_price):
    """
    Filter product records to only those with price greater than a specified minimum.
    
    Utility:
        Filters a list of product dictionaries based on a minimum price threshold,
        returning only products that exceed the specified price.
    
    Args:
        products (list): A list of product dictionaries, each containing at minimum
                        a 'price' key with a numeric value.
        min_price (float): The minimum price threshold. Products with price > min_price
                          will be included in the result.
    
    Returns:
        list: A list of product dictionaries that have a price greater than min_price.
              Returns an empty list if no products match the criteria.
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