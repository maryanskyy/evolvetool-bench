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
    
    result = {
        "version": None,
        "variables": [],
        "objective": {"type": None, "expression": None, "terms": []},
        "constraints": [],
        "bounds": {}
    }
    
    # Parse version
    version_match = re.search(r'ARCOPT:(\w+)', spec_string)
    if version_match:
        result["version"] = version_match.group(1)
    
    # Parse variables
    vars_match = re.search(r'VARS:([^;]+)', spec_string)
    if vars_match:
        result["variables"] = [v.strip() for v in vars_match.group(1).split(',')]
    
    # Parse objective function
    obj_match = re.search(r'OBJ:(\w+):([^;]+)', spec_string)
    if obj_match:
        result["objective"]["type"] = obj_match.group(1)
        expression = obj_match.group(2)
        result["objective"]["expression"] = expression
        result["objective"]["terms"] = _parse_objective_terms(expression)
    
    # Parse constraints
    constrs_match = re.search(r'CONSTRS:([^;]+)', spec_string)
    if constrs_match:
        constraints_str = constrs_match.group(1)
        result["constraints"] = _parse_constraints(constraints_str)
    
    # Parse bounds
    bounds_match = re.search(r'BOUNDS:(.+)$', spec_string)
    if bounds_match:
        bounds_str = bounds_match.group(1)
        result["bounds"] = _parse_bounds(bounds_str)
    
    return result


def _parse_objective_terms(expression):
    """Parse objective function expression into individual terms."""
    import re
    
    terms = []
    # Pattern to match terms like: coefficient*variable^power or coefficient*variable or constant
    pattern = r'([+-]?\d*\.?\d+)\*([a-zA-Z]\w*)?(?:\^(\d+))?'
    
    matches = re.finditer(pattern, expression)
    for match in matches:
        coefficient = float(match.group(1))
        variable = match.group(2)
        power = int(match.group(3)) if match.group(3) else (1 if variable else 0)
        
        term = {
            "coefficient": coefficient,
            "variable": variable,
            "power": power
        }
        terms.append(term)
    
    return terms


def _parse_constraints(constraints_str):
    """Parse constraint expressions."""
    import re
    
    constraints = []
    # Split by semicolon if multiple constraints
    constraint_list = [c.strip() for c in constraints_str.split(';') if c.strip()]
    
    for constraint in constraint_list:
        # Match pattern: expression operator bound
        match = re.match(r'(.+?)(<=|>=|=)(.+)', constraint)
        if match:
            lhs = match.group(1).strip()
            operator = match.group(2).strip()
            rhs = match.group(3).strip()
            
            constraints.append({
                "lhs": lhs,
                "operator": operator,
                "rhs": rhs
            })
    
    return constraints


def _parse_bounds(bounds_str):
    """Parse variable bounds."""
    import re
    
    bounds = {}
    # Pattern: variable:[lower,upper]
    pattern = r'(\w+):\[([^\]]+)\]'
    
    matches = re.finditer(pattern, bounds_str)
    for match in matches:
        variable = match.group(1)
        bound_str = match.group(2)
        
        # Parse lower and upper bounds
        parts = bound_str.split(',')
        lower = float(parts[0]) if parts[0] != '-inf' else float('-inf')
        upper = float(parts[1]) if parts[1] != '+inf' else float('inf')
        
        bounds[variable] = {"lower": lower, "upper": upper}
    
    return bounds