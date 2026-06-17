def parse_and_fit_arcfit_model(arcfit_spec):
    """
    Parse and fit an ARCFIT model specification using non-linear least squares.

    Utility:
        Parses ARCFIT curve-fitting format specifications and fits free parameters
        to provided data points using scipy's non-linear least squares optimization.
        Supports exponential decay, power law, and logistic models.

    Args:
        arcfit_spec (str): ARCFIT specification string in format:
            MODEL:<name>;PARAMS:<key>=<val_or_?>,...;DATA:<x1>,<y1>|<x2>,<y2>|...

    Returns:
        dict: JSON-compatible dictionary mapping parameter names to fitted values,
              rounded to 6 decimal places. Includes 'model' key with model name.
    """
    
    # Parse the ARCFIT specification
    model_match = re.search(r'MODEL:(\w+)', arcfit_spec)
    params_match = re.search(r'PARAMS:([^;]+)', arcfit_spec)
    data_match = re.search(r'DATA:(.+)$', arcfit_spec)

    if not all([model_match, params_match, data_match]):
        raise ValueError("Invalid ARCFIT specification format")

    model_name = model_match.group(1)
    params_str = params_match.group(1)
    data_str = data_match.group(1)

    # Parse parameters
    param_pairs = params_str.split(',')
    params = {}
    free_params = []
    fixed_params = {}

    for pair in param_pairs:
        key, val = pair.split('=')
        key = key.strip()
        val = val.strip()
        if val == '?':
            free_params.append(key)
            params[key] = None
        else:
            fixed_params[key] = float(val)
            params[key] = float(val)

    # Parse data points
    data_points = data_str.split('|')
    x_data = []
    y_data = []
    for point in data_points:
        x, y = point.split(',')
        x_data.append(float(x.strip()))
        y_data.append(float(y.strip()))

    x_data = np.array(x_data)
    y_data = np.array(y_data)

    # Define model functions that work with numpy arrays
    def exp_decay(x, a, b, c):
        return a * np.exp(-b * x) + c

    def power_law(x, a, b, c):
        return a * (x ** b) + c

    def logistic(x, L, k, x0):
        return L / (1 + np.exp(-k * (x - x0)))

    # Select model function
    models = {
        'exp_decay': exp_decay,
        'power_law': power_law,
        'logistic': logistic
    }

    if model_name not in models:
        raise ValueError(f"Unsupported model: {model_name}")

    model_func = models[model_name]

    # Create wrapper function with fixed parameters
    if fixed_params:
        def fit_func(x, *free_vals):
            all_params = dict(fixed_params)
            for i, param_name in enumerate(free_params):
                all_params[param_name] = free_vals[i]
            return model_func(x, **all_params)
    else:
        fit_func = model_func

    # Initial guess for free parameters
    p0 = [1.0] * len(free_params)

    # Perform curve fitting
    try:
        popt, _ = curve_fit(fit_func, x_data, y_data, p0=p0, maxfev=10000)
    except Exception as e:
        raise RuntimeError(f"Curve fitting failed: {str(e)}")

    # Build result dictionary
    result = {'model': model_name}
    for i, param_name in enumerate(free_params):
        result[param_name] = round(float(popt[i]), 6)
    for param_name, value in fixed_params.items():
        result[param_name] = round(value, 6)

    return result