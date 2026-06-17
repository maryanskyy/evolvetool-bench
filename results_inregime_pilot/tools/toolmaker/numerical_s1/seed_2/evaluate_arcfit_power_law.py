import json
import traceback

def evaluate_arcfit_power_law(fitted_model, params, query_points):
    """
    Evaluates an ARCFIT fitted power law model on query points.
    
    Args:
        fitted_model: String indicating the model type (e.g., 'power_law')
        params: String with comma-separated parameters in format 'a=value,b=value,c=value'
        query_points: String with comma-separated query x values
    
    Returns:
        JSON string containing list of predicted y values rounded to 6 decimal places
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
        predictions = []
        for x in x_values:
            y = a * (x ** b) + c
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            predictions.append(y_rounded)
        
        # Return as JSON string
        return json.dumps(predictions)
    
    except Exception as e:
        import sys
        traceback.print_exc(file=sys.stderr)
        raise