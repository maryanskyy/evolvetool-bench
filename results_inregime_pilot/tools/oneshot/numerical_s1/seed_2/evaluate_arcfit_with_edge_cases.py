def evaluate_arcfit_with_edge_cases(model_type: str, params_str: str, x_values_str: str) -> str:
    import json
    import math
    
    # Parse parameters
    params = {}
    for param in params_str.split(','):
        key, val = param.strip().split('=')
        params[key.strip()] = float(val.strip())
    
    # Parse x values
    x_values = [float(x.strip()) for x in x_values_str.split(',')]
    
    # Extract model parameters
    a = params.get('a', 1.0)
    b = params.get('b', 1.0)
    c = params.get('c', 0.0)
    
    results = []
    
    # Evaluate exponential decay model: y = a * exp(-b * x) + c
    if model_type.lower() == 'exp_decay':
        for x in x_values:
            try:
                # Calculate exponent
                exponent = -b * x
                
                # Handle extreme values to prevent overflow/underflow
                if exponent < -700:  # exp underflow threshold
                    exp_term = 0.0
                elif exponent > 700:  # exp overflow threshold
                    exp_term = float('inf')
                else:
                    exp_term = math.exp(exponent)
                
                # Calculate y value
                y = a * exp_term + c
                
                # Handle inf/nan cases
                if math.isinf(y) or math.isnan(y):
                    y = 0.0 if exponent < 0 else float('inf')
                
                # Treat very small values as 0
                if abs(y) < 1e-15:
                    y = 0.0
                
                # Round to 6 decimal places
                y_rounded = round(y, 6)
                results.append(y_rounded)
            except (OverflowError, ValueError):
                results.append(0.0)
    
    return json.dumps(results)