def fit_exponential_decay_model(spec_string):
    import json
    from math import exp, log
    
    # Parse the spec string
    parts = spec_string.split(';')
    model_type = parts[0].split(':')[1]
    data_str = parts[2].split(':')[1]
    
    # Parse data points
    data_points = []
    for point in data_str.split('|'):
        x, y = map(float, point.split(','))
        data_points.append((x, y))
    
    # Exponential decay model: y = a * exp(-b * x) + c
    # Use least squares fitting with iterative refinement
    
    # Initial parameter estimates
    a = max([y for x, y in data_points]) - min([y for x, y in data_points])
    c = min([y for x, y in data_points])
    b = 0.3
    
    # Levenberg-Marquardt-like iterative refinement
    learning_rate = 0.01
    for iteration in range(1000):
        # Calculate residuals and gradients
        residuals = []
        grad_a = 0
        grad_b = 0
        grad_c = 0
        
        for x, y in data_points:
            try:
                exp_term = exp(-b * x)
                predicted = a * exp_term + c
                residual = predicted - y
                residuals.append(residual ** 2)
                
                grad_a += 2 * residual * exp_term
                grad_b += 2 * residual * (-a * x * exp_term)
                grad_c += 2 * residual
            except:
                pass
        
        # Update parameters
        a -= learning_rate * grad_a / len(data_points)
        b -= learning_rate * grad_b / len(data_points)
        c -= learning_rate * grad_c / len(data_points)
        
        # Adaptive learning rate
        if iteration % 100 == 0:
            learning_rate *= 0.95
    
    # Ensure b is positive
    b = abs(b)
    
    # Round to 6 decimal places
    result = {
        'a': round(a, 6),
        'b': round(b, 6),
        'c': round(c, 6)
    }
    
    return json.dumps(result)