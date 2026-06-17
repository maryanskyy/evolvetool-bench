import json
import traceback

def evaluate_arcfit_power_law(fitted_model, params, query_points):
    """
    Evaluates an ARCFIT fitted power law model on query points.
    
    Args:
        fitted_model (str): The model type (e.g., 'power_law')
        params (str): Comma-separated parameters in format 'a=value,b=value,c=value'
        query_points (str): Comma-separated query x values
    
    Returns:
        str: JSON list of predicted y values rounded to 6 decimal places
    """
    try:
        # Parse parameters
        param_dict = {}
        for param in params.split(','):
            key, value = param.strip().split('=')
            param_dict[key.strip()] = float(value.strip())
        
        a = param_dict.get('a', 0.0)
        b = param_dict.get('b', 0.0)
        c = param_dict.get('c', 0.0)
        
        # Parse query points
        x_values = [float(x.strip()) for x in query_points.split(',')]
        
        # Evaluate power law model: y = a * x^b + c
        results = []
        for x in x_values:
            y = a * (x ** b) + c
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            results.append(y_rounded)
        
        # Return as JSON string
        return json.dumps(results)
    
    except Exception as e:
        import sys
        traceback.print_exc(file=sys.stderr)
        raise