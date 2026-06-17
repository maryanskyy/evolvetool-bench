def solve_arcopt_problem(spec: str) -> dict:
    """
    Solve an ARCOPT linear programming optimization problem.

    Utility:
        Parses an ARCOPT specification string and solves the linear programming
        problem using scipy.optimize.linprog. Returns the minimum objective value
        and the variable values at the optimum.

    Args:
        spec (str): ARCOPT specification string in format:
                   ARCOPT:v1;VARS:var1,var2,...;OBJ:linear:objective_expr;
                   CONSTRS:constraint1|constraint2|...;BOUNDS:var1:[min,max]|...

    Returns:
        dict: JSON-serializable dictionary with keys:
              - "minimum": float, the minimum objective value (rounded to 6 decimals)
              - "at": dict mapping variable names to their optimal values (rounded to 6 decimals)
    """
    
    # Parse the ARCOPT specification
    parts = spec.split(';')
    spec_dict = {}
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            spec_dict[key] = value

    # Extract variables
    vars_str = spec_dict.get('VARS', '')
    variables = [v.strip() for v in vars_str.split(',')]
    var_to_idx = {v: i for i, v in enumerate(variables)}

    # Extract objective function
    obj_str = spec_dict.get('OBJ', '')
    obj_parts = obj_str.split(':', 1)
    obj_expr = obj_parts[1] if len(obj_parts) > 1 else obj_parts[0]

    # Parse objective coefficients
    c = [0.0] * len(variables)
    for var in variables:
        pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + re.escape(var)
        match = re.search(pattern, obj_expr)
        if match:
            coeff_str = match.group(1).replace(' ', '')
            if coeff_str in ['+', '-', '']:
                coeff_str += '1'
            c[var_to_idx[var]] = float(coeff_str)

    # Extract constraints
    constrs_str = spec_dict.get('CONSTRS', '')
    constraints = [constr.strip() for constr in constrs_str.split('|')]

    A_ub = []
    b_ub = []
    A_eq = []
    b_eq = []

    for constraint in constraints:
        if not constraint:
            continue

        if '>=' in constraint:
            lhs, rhs = constraint.split('>=')
            rhs_val = float(rhs.strip())
            row = [0.0] * len(variables)
            for var in variables:
                pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + re.escape(var)
                match = re.search(pattern, lhs)
                if match:
                    coeff_str = match.group(1).replace(' ', '')
                    if coeff_str in ['+', '-', '']:
                        coeff_str += '1'
                    row[var_to_idx[var]] = -float(coeff_str)
            A_ub.append(row)
            b_ub.append(-rhs_val)
        elif '<=' in constraint:
            lhs, rhs = constraint.split('<=')
            rhs_val = float(rhs.strip())
            row = [0.0] * len(variables)
            for var in variables:
                pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + re.escape(var)
                match = re.search(pattern, lhs)
                if match:
                    coeff_str = match.group(1).replace(' ', '')
                    if coeff_str in ['+', '-', '']:
                        coeff_str += '1'
                    row[var_to_idx[var]] = float(coeff_str)
            A_ub.append(row)
            b_ub.append(rhs_val)
        elif '==' in constraint:
            lhs, rhs = constraint.split('==')
            rhs_val = float(rhs.strip())
            row = [0.0] * len(variables)
            for var in variables:
                pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + re.escape(var)
                match = re.search(pattern, lhs)
                if match:
                    coeff_str = match.group(1).replace(' ', '')
                    if coeff_str in ['+', '-', '']:
                        coeff_str += '1'
                    row[var_to_idx[var]] = float(coeff_str)
            A_eq.append(row)
            b_eq.append(rhs_val)

    # Extract bounds
    bounds_str = spec_dict.get('BOUNDS', '')
    bounds = [(0, None) for _ in variables]

    for bound_spec in bounds_str.split('|'):
        if ':' in bound_spec:
            var_name, range_str = bound_spec.split(':')
            var_name = var_name.strip()
            range_str = range_str.strip('[]')
            min_val, max_val = range_str.split(',')
            min_val = float(min_val.strip()) if min_val.strip() != '-inf' else None
            max_val = float(max_val.strip()) if max_val.strip() != '+inf' else None
            if var_name in var_to_idx:
                bounds[var_to_idx[var_name]] = (min_val, max_val)

    # Solve the linear programming problem
    result = linprog(c, A_ub=A_ub if A_ub else None, b_ub=b_ub if b_ub else None,
                     A_eq=A_eq if A_eq else None, b_eq=b_eq if b_eq else None,
                     bounds=bounds, method='highs')

    # Format the result
    minimum = round(float(result.fun), 6)
    at = {variables[i]: round(float(result.x[i]), 6) for i in range(len(variables))}

    return {"minimum": minimum, "at": at}