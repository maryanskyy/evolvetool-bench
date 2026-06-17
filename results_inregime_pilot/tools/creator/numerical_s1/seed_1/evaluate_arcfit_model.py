def evaluate_arcfit_model(spec_string):
    """
    Evaluate an ARCFIT fitted model on query points.
    
    Utility:
        Parses an ARCFIT specification string containing a fitted model type,
        parameters, and query points, then evaluates the model at those points
        and returns predictions rounded to 6 decimal places.
    
    Args:
        spec_string (str): A specification string in format:
            "FITTED:<model_type>;PARAMS:<param_list>;QUERY:<query_points>"
            Example: "FITTED:power_law;PARAMS:a=2.0,b=0.5,c=0.5;QUERY:36.0,49.0,64.0,100.0"
    
    Returns:
        list: A list of predicted y values (floats rounded to 6 decimal places)
    """
    import json
    
    # Parse the specification string
    parts = spec_string.split(';')
    
    fitted_part = parts[0].split(':')[1]
    model_type = fitted_part.strip()
    
    params_part = parts[1].split(':')[1]
    params_str = params_part.strip()
    params = {}
    for param in params_str.split(','):
        key, value = param.split('=')
        params[key.strip()] = float(value.strip())
    
    query_part = parts[2].split(':')[1]
    query_points = [float(x.strip()) for x in query_part.split(',')]
    
    # Evaluate based on model type
    predictions = []
    
    if model_type == 'power_law':
        # Power law model: y = a * x^b + c
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        
        for x in query_points:
            y = a * (x ** b) + c
            predictions.append(round(y, 6))
    
    elif model_type == 'exponential':
        # Exponential model: y = a * e^(b*x) + c
        import math
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        
        for x in query_points:
            y = a * math.exp(b * x) + c
            predictions.append(round(y, 6))
    
    elif model_type == 'linear':
        # Linear model: y = a*x + b
        a = params.get('a', 1.0)
        b = params.get('b', 0.0)
        
        for x in query_points:
            y = a * x + b
            predictions.append(round(y, 6))
    
    elif model_type == 'polynomial':
        # Polynomial model: y = a*x^2 + b*x + c
        a = params.get('a', 1.0)
        b = params.get('b', 0.0)
        c = params.get('c', 0.0)
        
        for x in query_points:
            y = a * (x ** 2) + b * x + c
            predictions.append(round(y, 6))
    
    return predictions