def fit_exponential_decay_model(data_str):
    import math
    
    # Parse data string
    points = []
    for pair in data_str.split('|'):
        x, y = map(float, pair.split(','))
        points.append((x, y))
    
    # Extract x and y values
    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]
    
    # Estimate c from asymptotic behavior (minimum y value)
    c = min(y_vals) * 0.9
    
    # Estimate a from first point: y[0] = a*exp(0) + c
    a = y_vals[0] - c
    
    # Estimate b using two points
    # y1 = a*exp(-b*x1) + c
    # y2 = a*exp(-b*x2) + c
    # (y1-c)/(y2-c) = exp(-b*(x1-x2))
    if len(points) >= 2:
        ratio = (y_vals[0] - c) / (y_vals[1] - c)
        if ratio > 0:
            b = math.log(ratio) / (x_vals[1] - x_vals[0])
        else:
            b = 0.1
    else:
        b = 0.1
    
    # Refine parameters using gradient descent
    learning_rate = 0.001
    for iteration in range(1000):
        # Calculate residuals
        residuals = []
        for i, (x, y) in enumerate(points):
            y_pred = a * math.exp(-b * x) + c
            residuals.append(y - y_pred)
        
        # Calculate gradients
        da = 0
        db = 0
        dc = 0
        for i, (x, y) in enumerate(points):
            y_pred = a * math.exp(-b * x) + c
            error = y - y_pred
            exp_term = math.exp(-b * x)
            da += -2 * error * exp_term
            db += -2 * error * a * x * exp_term
            dc += -2 * error
        
        # Update parameters
        a -= learning_rate * da / len(points)
        b -= learning_rate * db / len(points)
        c -= learning_rate * dc / len(points)
        
        # Ensure b stays positive
        if b < 0:
            b = abs(b)
    
    # Round to 6 decimal places
    a = round(a, 6)
    b = round(b, 6)
    c = round(c, 6)
    
    import json
    return json.dumps({"a": a, "b": b, "c": c})