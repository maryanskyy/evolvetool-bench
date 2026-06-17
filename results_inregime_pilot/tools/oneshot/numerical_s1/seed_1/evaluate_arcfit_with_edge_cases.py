def evaluate_arcfit_with_edge_cases(model_type: str, params_str: str, query_str: str) -> str:
    import json
    import math
    
    # Parse parameters
    params = {}
    for param in params_str.split(','):
        key, val = param.strip().split('=')
        params[key.strip()] = float(val.strip())
    
    # Parse query x values
    x_values = [float(x.strip()) for x in query_str.split(',')]
    
    # Evaluate based on model type
    results = []
    
    if model_type.lower() == 'exp_decay':
        a = params.get('a', 1.0)
        b = params.get('b', 1.0)
        c = params.get('c', 0.0)
        
        for x in x_values:
            try:
                # y = a * exp(-b * x) + c
                exponent = -b * x
                
                # Handle underflow: if exponent is very negative, result is 0
                if exponent < -700:  # exp(-700) is effectively 0
                    y = c
                else:
                    y = a * math.exp(exponent) + c
                
                # Check for NaN or Inf
                if math.isnan(y) or math.isinf(y):
                    y = 0.0 if exponent < 0 else float('inf')
                    if math.isinf(y):
                        y = 0.0
                
                # Round to 6 decimal places
                y_rounded = round(y, 6)
                results.append(y_rounded)
            except (ValueError, OverflowError):
                results.append(0.0)
    
    return json.dumps(results)