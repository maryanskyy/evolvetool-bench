def fit_power_law_model(model_spec: str) -> str:
    import json
    from math import log, exp
    
    # Parse the spec string
    parts = model_spec.split(';')
    data_part = parts[2].split(':')[1]
    
    # Parse data points
    points = []
    for pair in data_part.split('|'):
        x, y = map(float, pair.split(','))
        points.append((x, y))
    
    # Extract x and y values
    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]
    n = len(points)
    
    # Use iterative least squares to fit y = a * x^b + c
    # Start with initial guess: c ≈ min(y), then fit log-linear for a and b
    
    c = min(y_vals) * 0.9
    best_error = float('inf')
    best_params = {'a': 1.0, 'b': 0.5, 'c': c}
    
    # Try different c values
    for c_try in [min(y_vals) * i / 10 for i in range(-5, 5)]:
        # For fixed c, fit y - c = a * x^b using log transformation
        # log(y - c) = log(a) + b * log(x)
        
        try:
            valid = True
            log_x = []
            log_y = []
            
            for i in range(n):
                if y_vals[i] - c_try <= 0 or x_vals[i] <= 0:
                    valid = False
                    break
                log_x.append(log(x_vals[i]))
                log_y.append(log(y_vals[i] - c_try))
            
            if not valid:
                continue
            
            # Solve linear system: log_y = b * log_x + log_a
            sum_log_x = sum(log_x)
            sum_log_y = sum(log_y)
            sum_log_x2 = sum(lx * lx for lx in log_x)
            sum_log_xy = sum(log_x[i] * log_y[i] for i in range(n))
            
            denom = n * sum_log_x2 - sum_log_x * sum_log_x
            if abs(denom) < 1e-10:
                continue
            
            b = (n * sum_log_xy - sum_log_x * sum_log_y) / denom
            log_a = (sum_log_y - b * sum_log_x) / n
            a = exp(log_a)
            
            # Calculate error
            error = sum((y_vals[i] - (a * (x_vals[i] ** b) + c_try)) ** 2 for i in range(n))
            
            if error < best_error:
                best_error = error
                best_params = {'a': a, 'b': b, 'c': c_try}
        
        except (ValueError, ZeroDivisionError):
            continue
    
    # Round to 6 decimal places
    result = {
        'a': round(best_params['a'], 6),
        'b': round(best_params['b'], 6),
        'c': round(best_params['c'], 6)
    }
    
    return json.dumps(result)