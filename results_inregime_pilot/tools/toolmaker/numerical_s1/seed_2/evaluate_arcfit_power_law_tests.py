import json
import sys
from io import StringIO

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
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise

# Test 1: Original example from spec
try:
    result = evaluate_arcfit_power_law('power_law', 'a=2.0,b=0.5,c=0.5', '36.0,49.0,64.0,100.0')
    expected = [12.5, 14.5, 16.5, 20.5]
    parsed = json.loads(result)
    if parsed == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {parsed}")
except Exception as e:
    print(f"FAIL: {str(e)}")

# Test 2: Single query point
try:
    result = evaluate_arcfit_power_law('power_law', 'a=1.0,b=2.0,c=0.0', '5.0')
    expected = [25.0]
    parsed = json.loads(result)
    if parsed == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {parsed}")
except Exception as e:
    print(f"FAIL: {str(e)}")

# Test 3: With negative exponent
try:
    result = evaluate_arcfit_power_law('power_law', 'a=1.0,b=-1.0,c=0.0', '2.0,4.0,5.0')
    parsed = json.loads(result)
    expected = [0.5, 0.25, 0.2]
    # Check with tolerance for floating point
    if all(abs(p - e) < 1e-6 for p, e in zip(parsed, expected)):
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {parsed}")
except Exception as e:
    print(f"FAIL: {str(e)}")

# Test 4: With constant offset
try:
    result = evaluate_arcfit_power_law('power_law', 'a=2.0,b=1.0,c=3.0', '1.0,2.0,3.0')
    expected = [5.0, 7.0, 9.0]
    parsed = json.loads(result)
    if parsed == expected:
        print("PASS")
    else:
        print(f"FAIL: Expected {expected}, got {parsed}")
except Exception as e:
    print(f"FAIL: {str(e)}")

# Test 5: Rounding to 6 decimal places
try:
    result = evaluate_arcfit_power_law('power_law', 'a=1.0,b=0.333333,c=0.0', '8.0')
    parsed = json.loads(result)
    # 1.0 * (8.0^0.333333) + 0.0 should be approximately 2.0
    if len(parsed) == 1 and 1.9 < parsed[0] < 2.1:
        print("PASS")
    else:
        print(f"FAIL: Expected value near 2.0, got {parsed}")
except Exception as e:
    print(f"FAIL: {str(e)}")