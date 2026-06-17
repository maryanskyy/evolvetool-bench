def fit_power_law_model(spec_string):
    """
    Utility: Parses an ARCFIT model specification and fits a power law model
    of the form y = a + b*x^c to the provided data using least squares optimization.
    
    Args:
        spec_string (str): ARCFIT specification in format
            "MODEL:power_law;PARAMS:a=?,b=?,c=?;DATA:x1,y1|x2,y2|..."
    
    Returns:
        dict: JSON-compatible dictionary with fitted parameter values rounded to 6 decimal places
              Format: {"a": float, "b": float, "c": float}
    """
    import re
    from math import sqrt
    
    # Parse the specification string
    model_match = re.search(r'MODEL:(\w+)', spec_string)
    params_match = re.search(r'PARAMS:(.*?);', spec_string)
    data_match = re.search(r'DATA:(.*?)$', spec_string)
    
    if not all([model_match, params_match, data_match]):
        return {"error": "Invalid specification format"}
    
    model_type = model_match.group(1)
    if model_type != "power_law":
        return {"error": f"Unsupported model type: {model_type}"}
    
    # Parse parameters to fit
    params_str = params_match.group(1)
    param_names = [p.split('=')[0] for p in params_str.split(',')]
    
    # Parse data points
    data_str = data_match.group(1)
    data_points = []
    for point in data_str.split('|'):
        x, y = map(float, point.split(','))
        data_points.append((x, y))
    
    # Fit power law model: y = a + b*x^c using least squares
    # We'll use a numerical optimization approach
    def power_law(x, a, b, c):
        return a + b * (x ** c)
    
    def sum_squared_error(params, data):
        a, b, c = params
        error = 0
        for x, y in data:
            predicted = power_law(x, a, b, c)
            error += (y - predicted) ** 2
        return error
    
    # Initial guess: try to estimate parameters
    x_vals = [p[0] for p in data_points]
    y_vals = [p[1] for p in data_points]
    
    # Simple initial estimates
    a_init = min(y_vals) * 0.5
    c_init = 0.5
    b_init = (max(y_vals) - a_init) / (max(x_vals) ** c_init)
    
    # Gradient descent optimization
    params = [a_init, b_init, c_init]
    learning_rate = 0.001
    iterations = 5000
    
    for _ in range(iterations):
        a, b, c = params
        error = sum_squared_error(params, data_points)
        
        # Numerical gradient
        delta = 1e-5
        grad_a = (sum_squared_error([a + delta, b, c], data_points) - error) / delta
        grad_b = (sum_squared_error([a, b + delta, c], data_points) - error) / delta
        grad_c = (sum_squared_error([a, b, c + delta], data_points) - error) / delta
        
        # Update parameters
        params[0] -= learning_rate * grad_a
        params[1] -= learning_rate * grad_b
        params[2] -= learning_rate * grad_c
        
        # Adaptive learning rate
        if _ % 500 == 0:
            learning_rate *= 0.95
    
    a, b, c = params
    
    # Round to 6 decimal places
    result = {
        "a": round(a, 6),
        "b": round(b, 6),
        "c": round(c, 6)
    }
    
    return result