def fit_power_law_model(spec_string):
    """
    Utility: Parses an ARCFIT model specification and fits a power law model
    of the form y = a + b*x^c using least squares optimization.
    
    Args:
        spec_string (str): ARCFIT specification in format
            "MODEL:power_law;PARAMS:a=?,b=?,c=?;DATA:x1,y1|x2,y2|..."
    
    Returns:
        dict: JSON-compatible dictionary with fitted parameters rounded to 6 decimal places
              Format: {"a": float, "b": float, "c": float}
    """
    import re
    from math import log, exp
    
    # Parse the specification string
    model_match = re.search(r'MODEL:(\w+)', spec_string)
    data_match = re.search(r'DATA:(.*?)(?:;|$)', spec_string)
    
    if not model_match or not data_match:
        return {"error": "Invalid specification format"}
    
    model_type = model_match.group(1)
    data_str = data_match.group(1)
    
    # Parse data points
    data_points = []
    for point in data_str.split('|'):
        x, y = map(float, point.split(','))
        data_points.append((x, y))
    
    # Fit power law model: y = a + b*x^c
    # Use iterative least squares approach
    def residuals(params, data):
        a, b, c = params
        error = 0
        for x, y in data:
            predicted = a + b * (x ** c)
            error += (y - predicted) ** 2
        return error
    
    # Initial guess
    best_params = [0, 1, 0.5]
    best_error = float('inf')
    
    # Grid search followed by refinement
    for a_init in [0, 1, 2]:
        for b_init in [0.5, 1, 2]:
            for c_init in [0.3, 0.5, 0.7]:
                params = [a_init, b_init, c_init]
                
                # Simple gradient descent refinement
                learning_rate = 0.001
                for _ in range(1000):
                    error = residuals(params, data_points)
                    
                    if error < best_error:
                        best_error = error
                        best_params = params[:]
                    
                    # Numerical gradient
                    delta = 1e-5
                    for i in range(3):
                        params_plus = params[:]
                        params_plus[i] += delta
                        grad = (residuals(params_plus, data_points) - error) / delta
                        params[i] -= learning_rate * grad
    
    # Fine-tune with smaller learning rate
    params = best_params[:]
    learning_rate = 0.0001
    for _ in range(2000):
        error = residuals(params, data_points)
        delta = 1e-5
        for i in range(3):
            params_plus = params[:]
            params_plus[i] += delta
            grad = (residuals(params_plus, data_points) - error) / delta
            params[i] -= learning_rate * grad
    
    a, b, c = params
    
    # Round to 6 decimal places
    result = {
        "a": round(a, 6),
        "b": round(b, 6),
        "c": round(c, 6)
    }
    
    return result


# Test with the provided specification
spec = "MODEL:power_law;PARAMS:a=?,b=?,c=?;DATA:1.0,2.5|2.0,3.328427|4.0,4.5|9.0,6.5|16.0,8.5|25.0,10.5"
print(fit_power_law_model(spec))