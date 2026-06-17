def parse_and_fit_arcfit_model(spec: str) -> str:
    import json
    from math import sqrt, log
    
    # Parse the specification string
    parts = spec.split(';')
    model_type = None
    params = {}
    data_points = []
    
    for part in parts:
        if part.startswith('MODEL:'):
            model_type = part.split(':')[1]
        elif part.startswith('PARAMS:'):
            param_str = part.split(':')[1]
            for param in param_str.split(','):
                key = param.split('=')[0]
                params[key] = None
        elif part.startswith('DATA:'):
            data_str = part.split(':')[1]
            for point in data_str.split('|'):
                x, y = map(float, point.split(','))
                data_points.append((x, y))
    
    # For power_law model: y = a * x^b + c
    # Use least squares fitting
    n = len(data_points)
    
    # Initial guess using logarithmic transformation for power law
    # Transform: log(y - c) = log(a) + b*log(x)
    # Start with c = 0 for initial estimation
    
    sum_log_x = sum(log(x) for x, y in data_points)
    sum_log_y = sum(log(y) for x, y in data_points)
    sum_log_x_log_y = sum(log(x) * log(y) for x, y in data_points)
    sum_log_x_sq = sum(log(x) ** 2 for x, y in data_points)
    
    b = (n * sum_log_x_log_y - sum_log_x * sum_log_y) / (n * sum_log_x_sq - sum_log_x ** 2)
    log_a = (sum_log_y - b * sum_log_x) / n
    a = 2.718281828 ** log_a
    c = 0.0
    
    # Refine using Levenberg-Marquardt-like approach
    learning_rate = 0.01
    for iteration in range(100):
        residuals = [y - (a * (x ** b) + c) for x, y in data_points]
        sse = sum(r ** 2 for r in residuals)
        
        # Compute gradients
        da = sum(-2 * residuals[i] * (data_points[i][0] ** b) for i in range(n)) / n
        db = sum(-2 * residuals[i] * a * (data_points[i][0] ** b) * log(data_points[i][0]) for i in range(n)) / n
        dc = sum(-2 * residuals[i] for i in range(n)) / n
        
        # Update parameters
        a -= learning_rate * da
        b -= learning_rate * db
        c -= learning_rate * dc
        
        if iteration > 50 and sse < 0.001:
            break
    
    # Round to 6 decimal places
    result = {
        'a': round(a, 6),
        'b': round(b, 6),
        'c': round(c, 6)
    }
    
    return json.dumps(result)