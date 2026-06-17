import json
import traceback

def evaluate_arcfit_power_law(fitted_model, params, query_points):
    """
    Evaluates an ARCFIT fitted power law model on query points.
    
    Args:
        fitted_model (str): Model type, e.g. 'power_law'
        params (str): Comma-separated parameters in format 'a=value,b=value,c=value'
        query_points (str): Comma-separated query x values
    
    Returns:
        str: JSON list of predicted y values rounded to 6 decimal places
    """
    try:
        # Validate model type
        if fitted_model.strip() != 'power_law':
            raise ValueError(f"Unsupported model type: {fitted_model}")
        
        # Parse parameters
        param_dict = {}
        for param in params.split(','):
            key, value = param.strip().split('=')
            param_dict[key.strip()] = float(value.strip())
        
        # Extract parameters
        a = param_dict.get('a')
        b = param_dict.get('b')
        c = param_dict.get('c')
        
        if a is None or b is None or c is None:
            raise ValueError("Missing required parameters: a, b, c")
        
        # Parse query points
        x_values = [float(x.strip()) for x in query_points.split(',')]
        
        # Evaluate power law model: y = a * x^b + c
        predictions = []
        for x in x_values:
            y = a * (x ** b) + c
            # Round to 6 decimal places
            y_rounded = round(y, 6)
            predictions.append(y_rounded)
        
        # Return as JSON list
        return json.dumps(predictions)
    
    except Exception as e:
        import sys
        traceback.print_exc(file=sys.stderr)
        raise