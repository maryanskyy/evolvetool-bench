def evaluate_arcfit_exponential_decay(a, b, c, x_values_str):
    """
    Evaluates exponential decay model y = a * exp(-b * x) + c at given x values.
    
    Args:
        a (float): Amplitude parameter
        b (float): Decay rate parameter
        c (float): Offset parameter
        x_values_str (str): Comma-separated x values to evaluate
    
    Returns:
        str: JSON list of predicted y values rounded to 6 decimal places
    """
    import json
    import math
    
    # Parse input parameters
    a = float(a)
    b = float(b)
    c = float(c)
    
    # Parse x values from comma-separated string
    x_values = [float(x.strip()) for x in x_values_str.split(',')]
    
    results = []
    
    for x in x_values:
        try:
            # Calculate exponent
            exponent = -b * x
            
            # Handle potential overflow/underflow
            if exponent < -700:  # exp(-700) is effectively 0
                exp_result = 0.0
            elif exponent > 700:  # exp(700) would overflow
                exp_result = float('inf')
            else:
                exp_result = math.exp(exponent)
            
            # Calculate y value
            y = a * exp_result + c
            
            # Handle infinity and NaN cases
            if math.isinf(y) or math.isnan(y):
                y = 0.0
            
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            results.append(y_rounded)
        
        except (ValueError, OverflowError):
            # Fallback for any calculation errors
            results.append(0.0)
    
    return json.dumps(results)