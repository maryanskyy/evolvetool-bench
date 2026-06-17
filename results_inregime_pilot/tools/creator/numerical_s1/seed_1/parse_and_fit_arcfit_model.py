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
    parts = arcfit_spec.split(';')

    model_name = None
    params_dict = {}
    data_points = []

    for part in parts:
        if part.startswith('MODEL:'):
            model_name = part.split(':')[1]
        elif part.startswith('PARAMS:'):
            params_str = part.split(':')[1]
            for param in params_str.split(','):
                key, val = param.split('=')
                params_dict[key] = val
        elif part.startswith('DATA:'):
            data_str = part.split(':')[1]
            for point in data_str.split('|'):
                x, y = point.split(',')
                data_points.append((float(x), float(y)))

    # Extract x and y arrays as numpy arrays
    x_data = np.array([p[0] for p in data_points])
    y_data = np.array([p[1] for p in data_points])

    # Define model functions - use numpy for vectorized operations
    def exp_decay(x, a, b, c):
        return a * np.exp(-b * x) + c

    def power_law(x, a, b, c):
        return a * (x ** b) + c

    def logistic(x, L, k, x0):
        return L / (1 + np.exp(-k * (x - x0)))

    # Select model function
    if model_name == 'exp_decay':
        model_func = exp_decay
    elif model_name == 'power_law':
        model_func = power_law
    elif model_name == 'logistic':
        model_func = logistic
    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Identify free parameters and initial guesses
    free_params = []
    initial_guesses = []
    param_names = []

    for key in sorted(params_dict.keys()):
        val = params_dict[key]
        param_names.append(key)
        if val == '?':
            free_params.append(key)
            # Provide reasonable initial guesses
            if key == 'a':
                initial_guesses.append(1.0)
            elif key == 'b':
                initial_guesses.append(0.5)
            elif key == 'c':
                initial_guesses.append(0.0)
            elif key == 'L':
                initial_guesses.append(max(y_data))
            elif key == 'k':
                initial_guesses.append(1.0)
            elif key == 'x0':
                initial_guesses.append(sum(x_data) / len(x_data))
        else:
            params_dict[key] = float(val)

    # Fit the model
    try:
        popt, _ = curve_fit(model_func, x_data, y_data, p0=initial_guesses, maxfev=10000)
    except Exception as e:
        raise RuntimeError(f"Curve fitting failed: {e}")

    # Build result dictionary
    result = {'model': model_name}
    for i, param_name in enumerate(free_params):
        result[param_name] = round(float(popt[i]), 6)

    # Add fixed parameters
    for key, val in params_dict.items():
        if key not in result:
            result[key] = round(float(val), 6) if isinstance(val, (int, float, str)) else val

    return result