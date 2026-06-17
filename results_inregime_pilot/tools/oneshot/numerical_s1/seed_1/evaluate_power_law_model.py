def evaluate_power_law_model(a, b, c, query_points):
    """
    Evaluates a power law model on query points.
    Model: y = a * x^b + c
    
    Args:
        a (float): Coefficient parameter
        b (float): Exponent parameter
        c (float): Offset parameter
        query_points (str): Comma-separated query x values
    
    Returns:
        str: JSON list of predicted y values rounded to 6 decimal places
    """
    import json
    
    # Parse query points from comma-separated string
    try:
        x_values = [float(x.strip()) for x in query_points.split(',')]
    except (ValueError, AttributeError):
        return json.dumps({"error": "Invalid query points format"})
    
    # Evaluate power law model: y = a * x^b + c
    predictions = []
    for x in x_values:
        try:
            if x < 0 and b != int(b):
                # Cannot raise negative number to non-integer power
                predictions.append(None)
            else:
                y = a * (x ** b) + c
                # Round to 6 decimal places
                y_rounded = round(y, 6)
                predictions.append(y_rounded)
        except (ValueError, OverflowError):
            predictions.append(None)
    
    return json.dumps(predictions)