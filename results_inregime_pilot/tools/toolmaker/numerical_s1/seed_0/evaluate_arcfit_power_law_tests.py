import json
import sys
import traceback
from io import StringIO

def evaluate_arcfit_power_law(fitted_model, params, query_points):
    try:
        if fitted_model.strip() != 'power_law':
            raise ValueError(f"Unsupported model type: {fitted_model}")
        
        param_dict = {}
        for param in params.split(','):
            key, value = param.strip().split('=')
            param_dict[key.strip()] = float(value.strip())
        
        a = param_dict.get('a')
        b = param_dict.get('b')
        c = param_dict.get('c')
        
        if a is None or b is None or c is None:
            raise ValueError("Missing required parameters: a, b, c")
        
        x_values = [float(x.strip()) for x in query_points.split(',')]
        
        predictions = []
        for x in x_values:
            y = a * (x ** b) + c
            y_rounded = round(y, 6)
            predictions.append(y_rounded)
        
        return json.dumps(predictions)
    
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise

def test_basic_power_law():
    try:
        result = evaluate_arcfit_power_law('power_law', 'a=2.0,b=0.5,c=0.5', '36.0,49.0,64.0,100.0')
        expected = [12.5, 14.5, 16.5, 20.5]
        actual = json.loads(result)
        if actual == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {actual}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_query_point():
    try:
        result = evaluate_arcfit_power_law('power_law', 'a=1.0,b=2.0,c=0.0', '5.0')
        expected = [25.0]
        actual = json.loads(result)
        if actual == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {actual}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_with_negative_offset():
    try:
        result = evaluate_arcfit_power_law('power_law', 'a=3.0,b=1.0,c=-2.0', '4.0,10.0')
        expected = [10.0, 28.0]
        actual = json.loads(result)
        if actual == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {actual}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_rounding_precision():
    try:
        result = evaluate_arcfit_power_law('power_law', 'a=1.5,b=0.333,c=0.1', '8.0')
        actual = json.loads(result)
        if len(actual) == 1 and isinstance(actual[0], float):
            if actual[0] == round(1.5 * (8.0 ** 0.333) + 0.1, 6):
                print("PASS")
            else:
                print(f"FAIL: Rounding mismatch")
        else:
            print(f"FAIL: Unexpected result format")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_invalid_model_type():
    try:
        result = evaluate_arcfit_power_law('exponential', 'a=2.0,b=0.5,c=0.5', '36.0')
        print(f"FAIL: Should have raised ValueError for invalid model type")
    except ValueError as e:
        if "Unsupported model type" in str(e):
            print("PASS")
        else:
            print(f"FAIL: Wrong error message: {str(e)}")
    except Exception as e:
        print(f"FAIL: Unexpected exception: {str(e)}")

if __name__ == '__main__':
    test_basic_power_law()
    test_single_query_point()
    test_with_negative_offset()
    test_rounding_precision()
    test_invalid_model_type()