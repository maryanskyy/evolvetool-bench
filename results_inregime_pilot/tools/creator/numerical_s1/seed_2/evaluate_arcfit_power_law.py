def evaluate_arcfit_power_law(fitted_spec: str, query_points: str) -> list:
    """
    Evaluate an ARCFIT fitted power law model on query points.
    
    Utility:
        Parses an ARCFIT model specification string containing fitted parameters
        and evaluates the power law model on provided query points. Returns predicted
        y values rounded to 6 decimal places.
    
    Args:
        fitted_spec: String in format "FITTED:power_law;PARAMS:a=X,b=Y,c=Z"
                    containing the model type and fitted parameters
        query_points: Comma-separated string of x values to evaluate, e.g. "36.0,49.0,64.0,100.0"
    
    Returns:
        List of predicted y values (floats rounded to 6 decimal places)
    """
    import re
    
    # Parse the fitted specification
    fitted_match = re.search(r'FITTED:(\w+)', fitted_spec)
    model_type = fitted_match.group(1) if fitted_match else None
    
    # Parse parameters
    params_match = re.search(r'PARAMS:(.+?)(?:;|$)', fitted_spec)
    params_str = params_match.group(1) if params_match else ""
    
    params = {}
    for param in params_str.split(','):
        key, value = param.split('=')
        params[key.strip()] = float(value.strip())
    
    # Parse query points
    query_values = [float(x.strip()) for x in query_points.split(',')]
    
    # Evaluate power law model: y = a * (x ^ b) + c
    if model_type == 'power_law':
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        
        predictions = []
        for x in query_values:
            y = a * (x ** b) + c
            predictions.append(round(y, 6))
        
        return predictions
    
    return []