def fit_exponential_decay_model(spec_string):
    """
    Utility: Fits an exponential decay model of the form y = a * exp(-b*x) + c
    to data points using non-linear least squares optimization.

    Args:
        spec_string (str): ARCFIT specification string in format
            "MODEL:exp_decay;PARAMS:a=?,b=?,c=?;DATA:x1,y1|x2,y2|..."

    Returns:
        dict: JSON object with fitted parameter values rounded to 6 decimal places
              Format: {"a": float, "b": float, "c": float}
    """
    import re
    import math

    # Parse the specification string
    model_match = re.search(r'MODEL:(\w+)', spec_string)
    data_match = re.search(r'DATA:(.*?)(?:;|$)', spec_string)

    if not model_match or not data_match:
        raise ValueError("Invalid specification format")

    model_type = model_match.group(1)
    if model_type != 'exp_decay':
        raise ValueError(f"Unsupported model type: {model_type}")

    # Parse data points
    data_str = data_match.group(1)
    data_points = []
    for point in data_str.split('|'):
        x, y = map(float, point.split(','))
        data_points.append((x, y))

    # Initial parameter guesses
    y_values = [y for x, y in data_points]
    a_init = max(y_values) - min(y_values)
    b_init = 0.1
    c_init = min(y_values)

    # Levenberg-Marquardt-like optimization using gradient descent
    params = [a_init, b_init, c_init]
    learning_rate = 0.001
    iterations = 10000
    tolerance = 1e-8

    for iteration in range(iterations):
        # Calculate residuals and gradients
        residuals = []
        gradients = [0.0, 0.0, 0.0]

        for x, y in data_points:
            a, b, c = params
            
            # Clamp b*x to prevent overflow
            exp_arg = -b * x
            if exp_arg < -700:  # exp(-700) is effectively 0
                exp_term = 0.0
            else:
                exp_term = math.exp(exp_arg)
            
            y_pred = a * exp_term + c
            residual = y_pred - y
            residuals.append(residual)

            # Partial derivatives
            gradients[0] += 2 * residual * exp_term  # da
            if exp_arg >= -700:  # Only compute if exp_term is not effectively 0
                gradients[1] += 2 * residual * a * x * exp_term  # db
            gradients[2] += 2 * residual  # dc

        # Calculate sum of squared residuals
        ssr = sum(r**2 for r in residuals)

        # Update parameters with bounds checking
        new_params = [params[i] - learning_rate * gradients[i] for i in range(3)]
        
        # Ensure b stays positive and reasonable
        new_params[1] = max(0.0001, new_params[1])
        
        # Check convergence
        param_change = sum((new_params[i] - params[i])**2 for i in range(3))**0.5
        if param_change < tolerance:
            break

        params = new_params

        # Adaptive learning rate
        if iteration % 100 == 0 and iteration > 0:
            learning_rate *= 0.99

    # Round to 6 decimal places
    result = {
        "a": round(params[0], 6),
        "b": round(params[1], 6),
        "c": round(params[2], 6)
    }

    return result