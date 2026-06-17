def evaluate_arcfit_model(model_name, params_str, query_str):
    import math
    import json
    
    # Parse parameters
    params = {}
    for param_pair in params_str.split(','):
        key, val = param_pair.strip().split('=')
        params[key.strip()] = float(val.strip())
    
    # Parse query x values
    x_values = [float(x.strip()) for x in query_str.split(',')]
    
    # Define model formulas by name
    models = {
        'exp_decay': lambda x, p: p['a'] * math.exp(-p['b'] * x) + p['c'],
        'linear': lambda x, p: p['a'] * x + p['b'],
        'quadratic': lambda x, p: p['a'] * x**2 + p['b'] * x + p['c'],
        'power': lambda x, p: p['a'] * (x ** p['b']) + p['c'],
        'logarithmic': lambda x, p: p['a'] * math.log(x) + p['b']
    }
    
    # Get the model function
    if model_name not in models:
        return json.dumps({"error": f"Unknown model: {model_name}"})
    
    model_func = models[model_name]
    
    # Evaluate model at each x value
    results = []
    for x in x_values:
        try:
            y = model_func(x, params)
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            results.append(y_rounded)
        except Exception as e:
            return json.dumps({"error": f"Evaluation failed at x={x}: {str(e)}"})
    
    return json.dumps(results)