def fit_power_law_model(spec_string):
    """
    Utility: Fit a power law model (y = a*x^b + c) to data using least squares optimization.
    
    Args:
        spec_string (str): ARCFIT specification string in format 
                          "MODEL:power_law;PARAMS:a=?,b=?,c=?;DATA:x1,y1|x2,y2|..."
    
    Returns:
        dict: JSON object with fitted parameter values rounded to 6 decimal places
              Format: {"a": float, "b": float, "c": float}
    """
    import re
    from math import sqrt, log, exp
    
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
    
    if len(data_points) < 3:
        return {"error": "Need at least 3 data points"}
    
    # Fit power law model: y = a*x^b + c
    # Use iterative least squares approach
    def power_law(x, a, b, c):
        return a * (x ** b) + c
    
    def residual_sum_squares(params, data):
        a, b, c = params
        rss = 0
        for x, y in data:
            try:
                pred = power_law(x, a, b, c)
                rss += (y - pred) ** 2
            except:
                return float('inf')
        return rss
    
    # Initial parameter guesses
    best_params = [1.0, 0.5, 0.0]
    best_rss = residual_sum_squares(best_params, data_points)
    
    # Grid search followed by refinement
    for a_init in [0.1, 0.5, 1.0, 2.0, 5.0]:
        for b_init in [0.3, 0.5, 0.7, 1.0, 1.5]:
            for c_init in [-2.0, -1.0, 0.0, 1.0, 2.0]:
                params = [a_init, b_init, c_init]
                
                # Gradient descent refinement
                learning_rate = 0.001
                for _ in range(500):
                    rss = residual_sum_squares(params, data_points)
                    
                    # Numerical gradient
                    delta = 1e-6
                    grad = []
                    for i in range(3):
                        params_plus = params[:]
                        params_plus[i] += delta
                        rss_plus = residual_sum_squares(params_plus, data_points)
                        grad.append((rss_plus - rss) / delta)
                    
                    # Update parameters
                    for i in range(3):
                        params[i] -= learning_rate * grad[i]
                    
                    # Ensure a > 0 and b > 0
                    params[0] = max(0.001, params[0])
                    params[1] = max(0.001, params[1])
                
                final_rss = residual_sum_squares(params, data_points)
                if final_rss < best_rss:
                    best_rss = final_rss
                    best_params = params[:]
    
    # Round to 6 decimal places
    result = {
        "a": round(best_params[0], 6),
        "b": round(best_params[1], 6),
        "c": round(best_params[2], 6)
    }
    
    return result