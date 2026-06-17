def evaluate_arcfit_exponential_decay(a, b, c, x_values):
    """
    Evaluate an ARCFIT exponential decay model at specified x values.
    
    Utility:
        Safely evaluates the exponential decay function y = a * exp(-b*x) + c
        at edge-case x values (zero, negative, extremely large) without crashing
        or producing NaN. Handles exponential underflow gracefully by treating
        very small values as zero.
    
    Args:
        a (float): Amplitude parameter (default 1.0)
        b (float): Decay rate parameter (default 1.0)
        c (float): Vertical offset parameter (default 0.0)
        x_values (list or tuple of float): Query x values to evaluate
    
    Returns:
        list: JSON-serializable list of predicted y values rounded to 6 decimal places
    """
    import math
    import json
    
    results = []
    
    for x in x_values:
        try:
            # Calculate exponential decay: y = a * exp(-b*x) + c
            exponent = -b * x
            
            # Handle exponential underflow: if exponent is very negative,
            # exp() will underflow to 0, which is the desired behavior
            if exponent < -700:  # exp(-700) is effectively 0 in IEEE 754
                exp_term = 0.0
            else:
                exp_term = math.exp(exponent)
            
            y = a * exp_term + c
            
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            
            # Ensure no NaN or Inf values
            if math.isnan(y_rounded) or math.isinf(y_rounded):
                y_rounded = 0.0
            
            results.append(y_rounded)
        
        except (ValueError, OverflowError):
            # Fallback for any unexpected errors
            results.append(0.0)
    
    return results