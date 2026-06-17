def solve_arcopt_linear_program(spec: str) -> dict:
    """
    Utility: Solves ARCOPT linear programming optimization problems by parsing
    the specification string and using scipy.optimize.linprog to find the minimum.
    
    Args:
        spec (str): ARCOPT specification string in format:
                   ARCOPT:v1;VARS:var1,var2,...;OBJ:linear:objective_expr;
                   CONSTRS:constraint1|constraint2|...;BOUNDS:var1:[min,max]|...
    
    Returns:
        dict: JSON object with keys "minimum" (float) and "at" (dict of variable values),
              all values rounded to 6 decimal places.
    """
    import re
    from scipy.optimize import linprog
    import numpy as np
    
    # Parse the specification
    parts = spec.split(';')
    spec_dict = {}
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            spec_dict[key] = value
    
    # Extract variables
    vars_str = spec_dict.get('VARS', '')
    variables = [v.strip() for v in vars_str.split(',')]
    num_vars = len(variables)
    
    # Extract objective function
    obj_str = spec_dict.get('OBJ', '')
    obj_parts = obj_str.split(':', 1)
    obj_expr = obj_parts[1] if len(obj_parts) > 1 else obj_parts[0]
    
    # Parse objective coefficients
    c = [0] * num_vars
    for i, var in enumerate(variables):
        pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + re.escape(var)
        match = re.search(pattern, obj_expr)
        if match:
            coeff_str = match.group(1).replace(' ', '')
            if coeff_str in ['+', '-', '']:
                coeff_str += '1'
            c[i] = float(coeff_str)
    
    # Extract constraints
    constrs_str = spec_dict.get('CONSTRS', '')
    constraints = [c.strip() for c in constrs_str.split('|')]
    
    A_ub = []
    b_ub = []
    
    for constraint in constraints:
        # Parse constraint: e.g., "1*x1+1*x2>=4"
        if '>=' in constraint:
            lhs, rhs = constraint.split('>=')
            # Convert >= to <= by negating
            multiplier = -1
        elif '<=' in constraint:
            lhs, rhs = constraint.split('<=')
            multiplier = 1
        else:
            continue
        
        rhs_val = float(rhs.strip())
        row = [0] * num_vars
        
        for i, var in enumerate(variables):
            pattern = r'([+-]?\s*\d*\.?\d*)\s*\*?\s*' + re.escape(var)
            match = re.search(pattern, lhs)
            if match:
                coeff_str = match.group(1).replace(' ', '')
                if coeff_str in ['+', '-', '']:
                    coeff_str += '1'
                row[i] = float(coeff_str) * multiplier
        
        A_ub.append(row)
        b_ub.append(rhs_val * multiplier)
    
    # Extract bounds
    bounds_str = spec_dict.get('BOUNDS', '')
    bounds_list = [b.strip() for b in bounds_str.split('|')]
    bounds = [(0, None)] * num_vars
    
    for bound_spec in bounds_list:
        var_name, range_str = bound_spec.split(':')
        var_name = var_name.strip()
        range_str = range_str.strip('[]')
        min_val, max_val = range_str.split(',')
        
        var_idx = variables.index(var_name)
        min_val = float(min_val.strip()) if min_val.strip() != '-inf' else None
        max_val = float(max_val.strip()) if max_val.strip() != '+inf' else None
        bounds[var_idx] = (min_val, max_val)
    
    # Solve using linprog
    A_ub = np.array(A_ub) if A_ub else None
    b_ub = np.array(b_ub) if b_ub else None
    
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    
    # Format result
    minimum = round(float(result.fun), 6)
    solution = {var: round(float(result.x[i]), 6) for i, var in enumerate(variables)}
    
    return {"minimum": minimum, "at": solution}