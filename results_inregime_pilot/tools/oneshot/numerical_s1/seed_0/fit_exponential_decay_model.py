def fit_exponential_decay_model(data_str):
    import json
    from math import exp, sqrt
    
    # Parse data string
    points = []
    for pair in data_str.split('|'):
        x, y = map(float, pair.split(','))
        points.append((x, y))
    
    # Initial parameter guesses
    a = points[0][1] - points[-1][1]
    b = 0.1
    c = points[-1][1]
    
    # Levenberg-Marquardt-like optimization
    learning_rate = 0.01
    max_iterations = 1000
    tolerance = 1e-8
    
    for iteration in range(max_iterations):
        # Calculate residuals and gradients
        residuals = []
        grad_a = 0.0
        grad_b = 0.0
        grad_c = 0.0
        
        for x, y in points:
            exp_term = exp(-b * x)
            y_pred = a * exp_term + c
            residual = y_pred - y
            residuals.append(residual)
            
            grad_a += 2 * residual * exp_term
            grad_b += 2 * residual * a * x * exp_term
            grad_c += 2 * residual
        
        # Calculate sum of squared residuals
        ssr = sum(r * r for r in residuals)
        
        # Check convergence
        if ssr < tolerance:
            break
        
        # Update parameters
        a -= learning_rate * grad_a / len(points)
        b -= learning_rate * grad_b / len(points)
        c -= learning_rate * grad_c / len(points)
        
        # Adaptive learning rate
        if iteration % 100 == 0 and iteration > 0:
            learning_rate *= 0.95
    
    # Round to 6 decimal places
    a = round(a, 6)
    b = round(b, 6)
    c = round(c, 6)
    
    result = {"a": a, "b": b, "c": c}
    return json.dumps(result)