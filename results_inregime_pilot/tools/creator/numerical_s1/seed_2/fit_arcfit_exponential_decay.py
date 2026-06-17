def fit_arcfit_exponential_decay():
    """
    Utility: Fit an exponential decay model (y = a * exp(-b*x) + c) to ARCFIT data,
    evaluate predictions on specified x values, and compute statistics.

    Args: None (data and model are hardcoded per specification)

    Returns: dict with keys 'fitted_params', 'predictions', and 'stats'
    """
    
    # Parse the data
    data_str = "0.0,4.0|1.0,2.819592|2.0,2.103638|3.0,1.66939|4.0,1.406006|5.0,1.246255|6.0,1.149361"
    data_points = []
    for pair in data_str.split('|'):
        x, y = map(float, pair.split(','))
        data_points.append((x, y))

    x_data = [p[0] for p in data_points]
    y_data = [p[1] for p in data_points]

    # Fit exponential decay model: y = a * exp(-b*x) + c
    # Using least squares optimization with numerical methods
    def model(x, params):
        a, b, c = params
        return a * exp(-b * x) + c

    def residuals(params):
        return sum((model(x_data[i], params) - y_data[i])**2 for i in range(len(x_data)))

    # Initial guess based on data characteristics
    c_init = min(y_data)  # asymptotic value
    a_init = max(y_data) - c_init  # amplitude
    b_init = 0.3  # decay rate

    # Gradient descent optimization
    params = [a_init, b_init, c_init]
    learning_rate = 0.001
    iterations = 5000

    for _ in range(iterations):
        a, b, c = params

        # Compute gradients numerically
        delta = 1e-6

        grad_a = (residuals([a + delta, b, c]) - residuals([a - delta, b, c])) / (2 * delta)
        grad_b = (residuals([a, b + delta, c]) - residuals([a, b - delta, c])) / (2 * delta)
        grad_c = (residuals([a, b, c + delta]) - residuals([a, b, c - delta])) / (2 * delta)

        # Update parameters
        params[0] -= learning_rate * grad_a
        params[1] -= learning_rate * grad_b
        params[2] -= learning_rate * grad_c

        # Adaptive learning rate
        if _ % 500 == 0:
            learning_rate *= 0.95

    a, b, c = params
    fitted_params = {'a': round(a, 6), 'b': round(b, 6), 'c': round(c, 6)}

    # Evaluate on x = [0, 2, 4, 6, 8, 10]
    eval_x = [0, 2, 4, 6, 8, 10]
    predictions = [round(model(x, params), 6) for x in eval_x]

    # Compute statistics
    mean_val = sum(predictions) / len(predictions)
    sorted_preds = sorted(predictions)
    n = len(sorted_preds)
    median_val = (sorted_preds[n//2 - 1] + sorted_preds[n//2]) / 2 if n % 2 == 0 else sorted_preds[n//2]
    variance = sum((p - mean_val)**2 for p in predictions) / len(predictions)
    std_val = sqrt(variance)

    stats = {
        'mean': round(mean_val, 6),
        'median': round(median_val, 6),
        'std': round(std_val, 6)
    }

    return {
        'fitted_params': fitted_params,
        'predictions': predictions,
        'stats': stats
    }