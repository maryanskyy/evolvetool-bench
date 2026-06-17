def evaluate_arcfit_exponential_decay(a, b, c, x_values):
    """
    Evaluate an ARCFIT exponential decay model at specified x values.
    
    Utility:
        Safely evaluates the exponential decay model y = a * exp(-b * x) + c
        at edge-case x values (zero, negative, and extremely large values)
        without crashing or producing NaN. Handles exponential underflow by
        treating very small values as zero.
    
    Args:
        a (float): Amplitude parameter (default 1.0)
        b (float): Decay rate parameter (default 1.0)
        c (float): Offset parameter (default 0.0)
        x_values (list or tuple): List of x values to evaluate
    
    Returns:
        list: List of dicts with 'x' and 'y' keys, where y values are
              rounded to 6 decimal places. Very small values (< 1e-15)
              are treated as 0.0 to handle exponential underflow.
    """
    import math
    import json
    
    results = []
    
    for x in x_values:
        try:
            # Calculate exponential decay: y = a * exp(-b * x) + c
            exponent = -b * x
            
            # Handle potential overflow/underflow
            if exponent < -700:  # exp(-700) is effectively 0
                exp_value = 0.0
            elif exponent > 700:  # exp(700) would overflow
                exp_value = float('inf')
            else:
                exp_value = math.exp(exponent)
            
            # Calculate y value
            y = a * exp_value + c
            
            # Handle NaN and Inf cases
            if math.isnan(y) or math.isinf(y):
                y = 0.0
            
            # Treat very small values as zero
            if abs(y) < 1e-15:
                y = 0.0
            
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            
            results.append({
                "x": x,
                "y": y_rounded
            })
        except (ValueError, OverflowError):
            # Fallback for any unexpected errors
            results.append({
                "x": x,
                "y": 0.0
            })
    
    return results


# Execute with the specified parameters
if __name__ == "__main__":
    import json
    
    # ARCFIT model parameters
    a = 1.0
    b = 1.0
    c = 0.0
    
    # Query x values
    x_values = [0.0, -1.0, 100.0]
    
    # Evaluate the model
    results = evaluate_arcfit_exponential_decay(a, b, c, x_values)
    
    # Output as JSON
    print(json.dumps(results, indent=2))