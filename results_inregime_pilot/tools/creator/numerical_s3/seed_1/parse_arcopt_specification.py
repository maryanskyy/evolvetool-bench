def parse_arcopt_specification(spec_string):
    """
    Parse an ARCOPT problem specification into structured JSON representation.
    
    Utility:
        Parses ARCOPT v1 format specifications containing variables, objective functions,
        constraints, and variable bounds into a structured dictionary format.
    
    Args:
        spec_string (str): ARCOPT specification string in format:
            ARCOPT:v1;VARS:x1,x2;OBJ:type:expression;CONSTRS:constraint;BOUNDS:bounds
    
    Returns:
        dict: Structured representation with keys: version, variables, objective, 
              constraints, bounds
    """
    import re
    import json
    
    result = {}
    
    # Parse version
    version_match = re.search(r'ARCOPT:([^;]+)', spec_string)
    if version_match:
        result['version'] = version_match.group(1)
    
    # Parse variables
    vars_match = re.search(r'VARS:([^;]+)', spec_string)
    if vars_match:
        result['variables'] = [v.strip() for v in vars_match.group(1).split(',')]
    
    # Parse objective function
    obj_match = re.search(r'OBJ:([^:]+):([^;]+)', spec_string)
    if obj_match:
        obj_type = obj_match.group(1)
        obj_expr = obj_match.group(2)
        result['objective'] = {
            'type': obj_type,
            'expression': obj_expr,
            'terms': parse_objective_terms(obj_expr)
        }
    
    # Parse constraints
    constrs_match = re.search(r'CONSTRS:([^;]+)', spec_string)
    if constrs_match:
        constrs_str = constrs_match.group(1)
        result['constraints'] = parse_constraints(constrs_str)
    
    # Parse bounds
    bounds_match = re.search(r'BOUNDS:(.+)$', spec_string)
    if bounds_match:
        bounds_str = bounds_match.group(1)
        result['bounds'] = parse_bounds(bounds_str)
    
    return result


def parse_objective_terms(expression):
    """Parse objective function expression into individual terms."""
    import re
    
    terms = []
    # Match patterns like: coefficient*variable^power or coefficient*variable or constant
    pattern = r'([+-]?\d*\.?\d+)\*([a-zA-Z]\w*)\^(\d+)|([+-]?\d*\.?\d+)\*([a-zA-Z]\w*)|([+-]?\d+\.?\d*)'
    
    for match in re.finditer(pattern, expression):
        if match.group(1) is not None:  # coefficient*variable^power
            terms.append({
                'coefficient': float(match.group(1)),
                'variable': match.group(2),
                'power': int(match.group(3))
            })
        elif match.group(4) is not None:  # coefficient*variable
            terms.append({
                'coefficient': float(match.group(4)),
                'variable': match.group(5),
                'power': 1
            })
        elif match.group(6) is not None:  # constant
            terms.append({
                'coefficient': float(match.group(6)),
                'variable': None,
                'power': 0
            })
    
    return terms


def parse_constraints(constraints_str):
    """Parse constraint expressions."""
    import re
    
    constraints = []
    # Split by semicolon if multiple constraints
    constraint_list = constraints_str.split(';')
    
    for constraint in constraint_list:
        constraint = constraint.strip()
        if not constraint:
            continue
        
        # Match pattern: expression operator bound
        match = re.match(r'(.+?)(<=|>=|=)(.+)', constraint)
        if match:
            lhs = match.group(1).strip()
            operator = match.group(2)
            rhs = match.group(3).strip()
            
            constraints.append({
                'expression': lhs,
                'operator': operator,
                'bound': float(rhs),
                'terms': parse_objective_terms(lhs)
            })
    
    return constraints


def parse_bounds(bounds_str):
    """Parse variable bounds."""
    import re
    
    bounds = {}
    # Match pattern: var:[lower,upper]
    pattern = r'([a-zA-Z]\w*):?\[([^\]]+)\]'
    
    for match in re.finditer(pattern, bounds_str):
        var_name = match.group(1)
        bound_str = match.group(2)
        
        # Parse lower and upper bounds
        parts = bound_str.split(',')
        lower = float(parts[0].strip()) if parts[0].strip() != '-inf' else float('-inf')
        upper = float(parts[1].strip()) if parts[1].strip() != '+inf' else float('inf')
        
        bounds[var_name] = {
            'lower': lower,
            'upper': upper
        }
    
    return bounds


if __name__ == '__main__':
    spec = "ARCOPT:v1;VARS:x1,x2;OBJ:quadratic:1*x1^2+1*x2^2+-4*x1+-6*x2+13;CONSTRS:1*x1+1*x2<=4;BOUNDS:x1:[0,+inf]|x2:[0,+inf]"
    result = parse_arcopt_specification(spec)
    
    import json
    print(json.dumps(result, indent=2))