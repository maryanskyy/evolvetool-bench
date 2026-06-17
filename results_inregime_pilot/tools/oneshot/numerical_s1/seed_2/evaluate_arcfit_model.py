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
    def exp_decay(x, a, b, c):
        return a * math.exp(-b * x) + c
    
    def linear(x, a, b):
        return a * x + b
    
    def power(x, a, b, c):
        return a * (x ** b) + c
    
    def polynomial(x, a, b, c, d):
        return a * (x ** 2) + b * x + c + d
    
    # Map model names to functions
    models = {
        'exp_decay': exp_decay,
        'linear': linear,
        'power': power,
        'polynomial': polynomial
    }
    
    # Get the model function
    if model_name not in models:
        return json.dumps({'error': f'Unknown model: {model_name}'})
    
    model_func = models[model_name]
    
    # Evaluate model on query x values
    results = []
    for x in x_values:
        try:
            y = model_func(x, **params)
            results.append(round(y, 6))
        except Exception as e:
            return json.dumps({'error': f'Evaluation failed for x={x}: {str(e)}'})
    
    return json.dumps(results)