def evaluate_power_law_model(a, b, c, query_points):
    """
    Evaluates a power law model: y = a * (x ** b) + c
    
    Args:
        a (float): Coefficient parameter
        b (float): Exponent parameter
        c (float): Offset parameter
        query_points (str): Comma-separated query x values
    
    Returns:
        str: JSON list of predicted y values rounded to 6 decimal places
    """
    import json
    
    # Parse query points
    try:
        points = [float(x.strip()) for x in query_points.split(',')]
    except (ValueError, AttributeError):
        return json.dumps({"error": "Invalid query points format"})
    
    # Evaluate power law model: y = a * (x ** b) + c
    predictions = []
    for x in points:
        try:
            y = a * (x ** b) + c
            predictions.append(round(y, 6))
        except (ValueError, ZeroDivisionError) as e:
            return json.dumps({"error": f"Evaluation failed for x={x}: {str(e)}"})
    
    return json.dumps(predictions)