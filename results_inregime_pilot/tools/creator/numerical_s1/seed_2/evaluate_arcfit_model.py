def evaluate_arcfit_model(fitted_spec: str) -> list:
    """
    Evaluate a previously fitted ARCFIT model on new x values.
    
    Utility:
        Parses a fitted model specification string and evaluates the model
        at given query x values. Supports common model formulas like exponential
        decay: y = a * exp(-b * x) + c
    
    Args:
        fitted_spec (str): A specification string in format:
            FITTED:<name>;PARAMS:<key>=<val>,...;QUERY:<x1>,<x2>,...
            Example: "FITTED:exp_decay;PARAMS:a=3.0,b=0.5,c=1.0;QUERY:0.5,1.5,2.5,7.0"
    
    Returns:
        list: A list of predicted y values, each rounded to 6 decimal places.
              Example: [3.336403, 2.41710, 1.859514, 1.009075]
    """
    import math
    
    # Parse the specification string
    parts = fitted_spec.split(';')
    
    model_name = None
    params = {}
    query_values = []
    
    for part in parts:
        if part.startswith('FITTED:'):
            model_name = part.replace('FITTED:', '').strip()
        elif part.startswith('PARAMS:'):
            params_str = part.replace('PARAMS:', '').strip()
            for param_pair in params_str.split(','):
                key, val = param_pair.split('=')
                params[key.strip()] = float(val.strip())
        elif part.startswith('QUERY:'):
            query_str = part.replace('QUERY:', '').strip()
            query_values = [float(x.strip()) for x in query_str.split(',')]
    
    # Define model formulas
    def exp_decay(x, a, b, c):
        """Exponential decay model: y = a * exp(-b * x) + c"""
        return a * math.exp(-b * x) + c
    
    def linear(x, m, b):
        """Linear model: y = m * x + b"""
        return m * x + b
    
    def polynomial(x, coeffs):
        """Polynomial model: y = sum(coeff * x^i)"""
        result = 0
        for i, coeff in enumerate(coeffs):
            result += coeff * (x ** i)
        return result
    
    # Select and apply the appropriate model
    results = []
    
    if model_name == 'exp_decay':
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        for x in query_values:
            y = exp_decay(x, a, b, c)
            results.append(round(y, 6))
    
    elif model_name == 'linear':
        m = params.get('m', 1.0)
        b = params.get('b', 0.0)
        for x in query_values:
            y = linear(x, m, b)
            results.append(round(y, 6))
    
    else:
        # Default to exponential decay if model not recognized
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        for x in query_values:
            y = exp_decay(x, a, b, c)
            results.append(round(y, 6))
    
    return results