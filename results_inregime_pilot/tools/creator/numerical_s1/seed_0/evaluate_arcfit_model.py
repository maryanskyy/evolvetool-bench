def evaluate_arcfit_model(fitted_spec: str) -> list:
    """
    Evaluate a previously fitted ARCFIT model on new x values.
    
    Utility:
        Parses a fitted model specification string and evaluates the model
        at given query x values. Supports various model types (exp_decay, linear, etc.)
        and returns predicted y values rounded to 6 decimal places.
    
    Args:
        fitted_spec (str): A specification string in format:
            FITTED:<name>;PARAMS:<key>=<val>,...;QUERY:<x1>,<x2>,...
            Example: "FITTED:exp_decay;PARAMS:a=3.0,b=0.5,c=1.0;QUERY:0.5,1.5,2.5,7.0"
    
    Returns:
        list: A list of predicted y values (floats) rounded to 6 decimal places.
    
    Supported Models:
        - exp_decay: y = a * exp(-b * x) + c
        - linear: y = a * x + b
        - power: y = a * x^b + c
        - polynomial: y = a + b*x + c*x^2 + d*x^3 + ...
    """
    import math
    import re
    
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
            param_pairs = params_str.split(',')
            for pair in param_pairs:
                key, val = pair.split('=')
                params[key.strip()] = float(val.strip())
        elif part.startswith('QUERY:'):
            query_str = part.replace('QUERY:', '').strip()
            query_values = [float(x.strip()) for x in query_str.split(',')]
    
    # Define model evaluation functions
    def eval_exp_decay(x, params):
        """Exponential decay: y = a * exp(-b * x) + c"""
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        return a * math.exp(-b * x) + c
    
    def eval_linear(x, params):
        """Linear: y = a * x + b"""
        a = params.get('a', 1.0)
        b = params.get('b', 0.0)
        return a * x + b
    
    def eval_power(x, params):
        """Power: y = a * x^b + c"""
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        return a * (x ** b) + c
    
    def eval_polynomial(x, params):
        """Polynomial: y = a + b*x + c*x^2 + d*x^3 + ..."""
        result = 0.0
        for key in sorted(params.keys()):
            if key.isalpha():
                coeff = params[key]
                power = ord(key) - ord('a')
                result += coeff * (x ** power)
        return result
    
    # Select the appropriate model evaluator
    model_evaluators = {
        'exp_decay': eval_exp_decay,
        'linear': eval_linear,
        'power': eval_power,
        'polynomial': eval_polynomial
    }
    
    evaluator = model_evaluators.get(model_name, eval_exp_decay)
    
    # Evaluate the model at each query point
    results = []
    for x in query_values:
        y = evaluator(x, params)
        results.append(round(y, 6))
    
    return results