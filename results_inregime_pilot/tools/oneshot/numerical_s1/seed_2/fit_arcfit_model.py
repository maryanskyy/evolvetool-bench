def fit_arcfit_model(spec_string):
    import json
    from math import exp, log
    
    # Parse the ARCFIT specification
    parts = spec_string.split(';')
    model_part = parts[0].replace('MODEL:', '')
    params_part = parts[1].replace('PARAMS:', '')
    data_part = parts[2].replace('DATA:', '')
    
    model_name = model_part.strip()
    
    # Parse parameters
    param_specs = params_part.split(',')
    params = {}
    free_params = []
    for spec in param_specs:
        key, val = spec.split('=')
        key = key.strip()
        val = val.strip()
        if val == '?':
            free_params.append(key)
            params[key] = None
        else:
            params[key] = float(val)
    
    # Parse data points
    data_points = []
    for point in data_part.split('|'):
        x, y = point.split(',')
        data_points.append((float(x), float(y)))
    
    # Define model functions
    def exp_decay(x, a, b, c):
        return a * exp(-b * x) + c
    
    def power_law(x, a, b, c):
        return a * (x ** b) + c
    
    def logistic(x, L, k, x0):
        return L / (1 + exp(-k * (x - x0)))
    
    # Objective function: sum of squared residuals
    def objective(free_vals):
        test_params = params.copy()
        for i, key in enumerate(free_params):
            test_params[key] = free_vals[i]
        
        residual_sum = 0
        for x, y in data_points:
            if model_name == 'exp_decay':
                y_pred = exp_decay(x, test_params['a'], test_params['b'], test_params['c'])
            elif model_name == 'power_law':
                y_pred = power_law(x, test_params['a'], test_params['b'], test_params['c'])
            elif model_name == 'logistic':
                y_pred = logistic(x, test_params['L'], test_params['k'], test_params['x0'])
            residual_sum += (y - y_pred) ** 2
        return residual_sum
    
    # Initial guess for free parameters
    initial_guess = [1.0] * len(free_params)
    if model_name == 'exp_decay':
        initial_guess = [3.0, 0.5, 1.0]
    
    # Simple Nelder-Mead optimization
    best_vals = initial_guess[:len(free_params)]
    best_error = objective(best_vals)
    
    for iteration in range(1000):
        for i in range(len(best_vals)):
            for delta in [0.001, -0.001]:
                test_vals = best_vals[:]
                test_vals[i] += delta
                error = objective(test_vals)
                if error < best_error:
                    best_error = error
                    best_vals = test_vals
    
    # Store fitted values
    for i, key in enumerate(free_params):
        params[key] = round(best_vals[i], 6)
    
    # Return only the fitted parameters as JSON
    result = {k: v for k, v in params.items() if v is not None}
    return json.dumps(result)