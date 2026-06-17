def evaluate_arcfit_power_law(spec_string):
    """
    Evaluate an ARCFIT fitted power law model on query points.
    
    Utility:
        Parses an ARCFIT specification string containing a fitted power law model
        and its parameters, then evaluates the model on provided query points.
        Returns predicted y values rounded to 6 decimal places.
    
    Args:
        spec_string (str): A specification string in format:
            "FITTED:power_law;PARAMS:a=2.0,b=0.5,c=0.5;QUERY:36.0,49.0,64.0,100.0"
            where:
            - FITTED: model type (power_law)
            - PARAMS: comma-separated key=value pairs for model parameters (a, b, c)
            - QUERY: comma-separated query points (x values)
    
    Returns:
        list: JSON-compatible list of predicted y values rounded to 6 decimal places
    
    Power Law Model:
        y = a * (x ** b) + c
    """
    import json
    
    # Parse the specification string
    parts = spec_string.split(';')
    
    # Extract model type
    fitted_part = parts[0].split(':')[1]
    
    # Extract parameters
    params_part = parts[1].split(':')[1]
    params = {}
    for param in params_part.split(','):
        key, value = param.split('=')
        params[key.strip()] = float(value.strip())
    
    # Extract query points
    query_part = parts[2].split(':')[1]
    query_points = [float(x.strip()) for x in query_part.split(',')]
    
    # Get parameters for power law model
    a = params.get('a', 1.0)
    b = params.get('b', 1.0)
    c = params.get('c', 0.0)
    
    # Evaluate power law model: y = a * (x ** b) + c
    predictions = []
    for x in query_points:
        y = a * (x ** b) + c
        # Round to 6 decimal places
        y_rounded = round(y, 6)
        predictions.append(y_rounded)
    
    return predictions


# Example usage
if __name__ == "__main__":
    spec = "FITTED:power_law;PARAMS:a=2.0,b=0.5,c=0.5;QUERY:36.0,49.0,64.0,100.0"
    result = evaluate_arcfit_power_law(spec)
    print(result)