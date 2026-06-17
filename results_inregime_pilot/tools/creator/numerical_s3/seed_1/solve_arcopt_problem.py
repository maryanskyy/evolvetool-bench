def solve_arcopt_problem(spec: str) -> dict:
    """
    Utility: Solves ARCOPT linear/quadratic optimization problems by parsing the specification
    and using scipy.optimize to find the minimum value and optimal variable assignments.
    
    Args:
        spec (str): ARCOPT specification string in format:
                   ARCOPT:v1;VARS:var1,var2,...;OBJ:linear:objective_expr;CONSTRS:constraint1|constraint2|...;BOUNDS:var1:[min,max]|var2:[min,max]|...
    
    Returns:
        dict: JSON-serializable dictionary with keys:
              - "minimum": float value of objective at optimum (rounded to 6 decimals)
              - "at": dict mapping variable names to their optimal values (rounded to 6 decimals)
    """
    from scipy.optimize import linprog, minimize
    import re
    
    # Parse the ARCOPT specification
    parts = spec.split(';')
    spec_dict = {}
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            spec_dict[key] = value
    
    # Extract variables
    variables = spec_dict['VARS'].split(',')
    num_vars = len(variables)
    var_index = {var: i for i, var in enumerate(variables)}
    
    # Extract objective
    obj_parts = spec_dict['OBJ'].split(':')
    obj_type = obj_parts[0]
    obj_expr = obj_parts[1]
    
    # Parse objective coefficients
    c = [0.0] * num_vars
    for var in variables:
        pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + var
        match = re.search(pattern, obj_expr)
        if match:
            coeff_str = match.group(1).replace(' ', '')
            if coeff_str in ['+', '-', '']:
                coeff = 1.0 if coeff_str != '-' else -1.0
            else:
                coeff = float(coeff_str)
            c[var_index[var]] = coeff
    
    # Extract bounds
    bounds = [(0, None) for _ in variables]
    if 'BOUNDS' in spec_dict:
        bounds_str = spec_dict['BOUNDS']
        for bound_pair in bounds_str.split('|'):
            var_name, range_str = bound_pair.split(':')
            range_str = range_str.strip('[]')
            min_val, max_val = range_str.split(',')
            min_val = float(min_val) if min_val != '-inf' else None
            max_val = float(max_val) if max_val != '+inf' else None
            bounds[var_index[var_name]] = (min_val, max_val)
    
    # Extract and parse constraints
    A_ub = []
    b_ub = []
    if 'CONSTRS' in spec_dict:
        constraints = spec_dict['CONSTRS'].split('|')
        for constraint in constraints:
            constraint = constraint.strip()
            if '>=' in constraint:
                lhs, rhs = constraint.split('>=')
                # Convert >= to <= by negating
                coeffs = [0.0] * num_vars
                for var in variables:
                    pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + var
                    match = re.search(pattern, lhs)
                    if match:
                        coeff_str = match.group(1).replace(' ', '')
                        if coeff_str in ['+', '-', '']:
                            coeff = 1.0 if coeff_str != '-' else -1.0
                        else:
                            coeff = float(coeff_str)
                        coeffs[var_index[var]] = -coeff
                A_ub.append(coeffs)
                b_ub.append(-float(rhs.strip()))
            elif '<=' in constraint:
                lhs, rhs = constraint.split('<=')
                coeffs = [0.0] * num_vars
                for var in variables:
                    pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + var
                    match = re.search(pattern, lhs)
                    if match:
                        coeff_str = match.group(1).replace(' ', '')
                        if coeff_str in ['+', '-', '']:
                            coeff = 1.0 if coeff_str != '-' else -1.0
                        else:
                            coeff = float(coeff_str)
                        coeffs[var_index[var]] = coeff
                A_ub.append(coeffs)
                b_ub.append(float(rhs.strip()))
    
    # Solve using linprog
    result = linprog(c, A_ub=A_ub if A_ub else None, b_ub=b_ub if b_ub else None,
                     bounds=bounds, method='highs')
    
    # Format result
    minimum = round(float(result.fun), 6)
    solution = {var: round(float(result.x[var_index[var]]), 6) for var in variables}
    
    return {"minimum": minimum, "at": solution}