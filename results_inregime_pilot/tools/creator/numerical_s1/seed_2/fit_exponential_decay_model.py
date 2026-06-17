def fit_exponential_decay_model(model_spec):
    """
    Fit an exponential decay model to data points using least squares optimization.
    
    Utility:
        Parses an ARCFIT model specification string, extracts data points and parameters,
        and fits an exponential decay model of the form: y = a * exp(-b * x) + c
        Returns fitted parameter values rounded to 6 decimal places.
    
    Args:
        model_spec (str): ARCFIT format specification string containing:
            - MODEL: model type (exp_decay)
            - PARAMS: parameter names with ? for unknowns (a=?,b=?,c=?)
            - DATA: comma-separated x,y pairs separated by pipes (x1,y1|x2,y2|...)
    
    Returns:
        dict: JSON-compatible dictionary with fitted parameters rounded to 6 decimal places
              Example: {"a": 5.123456, "b": 0.234567, "c": 0.012345}
    """
    import re
    from math import exp, log
    
    # Parse the specification string
    model_match = re.search(r'MODEL:(\w+)', model_spec)
    params_match = re.search(r'PARAMS:(.*?);', model_spec)
    data_match = re.search(r'DATA:(.*?)$', model_spec)
    
    model_type = model_match.group(1) if model_match else None
    params_str = params_match.group(1) if params_match else ""
    data_str = data_match.group(1) if data_match else ""
    
    # Extract parameter names
    param_names = [p.split('=')[0].strip() for p in params_str.split(',')]
    
    # Parse data points
    data_pairs = data_str.split('|')
    x_data = []
    y_data = []
    for pair in data_pairs:
        x, y = map(float, pair.split(','))
        x_data.append(x)
        y_data.append(y)
    
    # Fit exponential decay: y = a * exp(-b * x) + c
    # Use iterative least squares approach
    
    def residuals(a, b, c):
        return sum((y_data[i] - (a * exp(-b * x_data[i]) + c)) ** 2 for i in range(len(x_data)))
    
    # Initial parameter estimates
    c_init = min(y_data)  # asymptotic value
    a_init = max(y_data) - c_init  # amplitude
    b_init = 0.3  # decay rate
    
    # Simple gradient descent optimization
    best_params = [a_init, b_init, c_init]
    best_error = residuals(*best_params)
    
    learning_rate = 0.01
    iterations = 5000
    
    for iteration in range(iterations):
        a, b, c = best_params
        
        # Compute gradients numerically
        delta = 1e-5
        
        grad_a = (residuals(a + delta, b, c) - residuals(a - delta, b, c)) / (2 * delta)
        grad_b = (residuals(a, b + delta, c) - residuals(a, b - delta, c)) / (2 * delta)
        grad_c = (residuals(a, b, c + delta) - residuals(a, b, c - delta)) / (2 * delta)
        
        # Update parameters
        a -= learning_rate * grad_a
        b -= learning_rate * grad_b
        c -= learning_rate * grad_c
        
        # Ensure b stays positive
        b = max(b, 0.001)
        
        error = residuals(a, b, c)
        
        if error < best_error:
            best_error = error
            best_params = [a, b, c]
            learning_rate *= 1.001
        else:
            learning_rate *= 0.95
        
        if learning_rate < 1e-8:
            break
    
    # Round to 6 decimal places
    result = {
        param_names[0]: round(best_params[0], 6),
        param_names[1]: round(best_params[1], 6),
        param_names[2]: round(best_params[2], 6)
    }
    
    return result


# Test with the provided specification
spec = "MODEL:exp_decay;PARAMS:a=?,b=?,c=?;DATA:0.0,5.5|1.0,4.204091|2.0,3.244058|3.0,2.532848|5.0,1.615651|8.0,0.95359|10.0,0.748935"
print(fit_exponential_decay_model(spec))