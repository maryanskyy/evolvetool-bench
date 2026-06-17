def evaluate_power_law_model(a, b, c, query_points):
    """
    Evaluates a power law model: y = a * (x ^ b) + c
    
    Args:
        a: coefficient parameter (float)
        b: exponent parameter (float)
        c: offset parameter (float)
        query_points: comma-separated string of x values to evaluate
    
    Returns:
        JSON string list of predicted y values rounded to 6 decimal places
    """
    import json
    
    # Parse query points
    try:
        x_values = [float(x.strip()) for x in query_points.split(',')]
    except (ValueError, AttributeError):
        return json.dumps({"error": "Invalid query points format"})
    
    # Evaluate power law model: y = a * (x ^ b) + c
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