def parse_arcopt_specification(spec_string):
    import json
    import re
    
    # Split by semicolon to get sections
    sections = spec_string.split(';')
    result = {
        'vars': [],
        'objective': {'type': '', 'coeffs': {}},
        'constraints': [],
        'bounds': {}
    }
    
    for section in sections:
        if section.startswith('VARS:'):
            vars_str = section[5:]
            result['vars'] = [v.strip() for v in vars_str.split(',')]
        
        elif section.startswith('OBJ:'):
            obj_str = section[4:]
            parts = obj_str.split(':', 1)
            result['objective']['type'] = parts[0]
            expr = parts[1] if len(parts) > 1 else ''
            
            # Parse coefficients from expression
            # Handle terms like: 3*x1, 2*x2, 1*x1^2, etc.
            terms = re.findall(r'([+-]?\d*\.?\d+)\*([a-zA-Z0-9_^*]+)', expr)
            for coeff, var in terms:
                result['objective']['coeffs'][var] = float(coeff)
        
        elif section.startswith('CONSTRS:'):
            constrs_str = section[8:]
            if constrs_str != 'NONE':
                constraints = constrs_str.split('|')
                for constraint in constraints:
                    constraint = constraint.strip()
                    # Match pattern: lhs_expr op rhs
                    match = re.match(r'(.+?)\s*(<=|>=|==)\s*(.+)', constraint)
                    if match:
                        lhs = match.group(1).strip()
                        op = match.group(2).strip()
                        rhs = match.group(3).strip()
                        try:
                            rhs_val = float(rhs)
                        except:
                            rhs_val = rhs
                        result['constraints'].append({
                            'lhs': lhs,
                            'op': op,
                            'rhs': rhs_val
                        })
        
        elif section.startswith('BOUNDS:'):
            bounds_str = section[7:]
            if bounds_str != 'NONE':
                bounds = bounds_str.split('|')
                for bound in bounds:
                    bound = bound.strip()
                    # Match pattern: var:[lo,hi]
                    match = re.match(r'([a-zA-Z0-9_]+):\[([^,]+),([^\]]+)\]', bound)
                    if match:
                        var = match.group(1)
                        lo = match.group(2).strip()
                        hi = match.group(3).strip()
                        
                        lo_val = None if lo in ['-inf', '+inf'] else float(lo)
                        hi_val = None if hi in ['-inf', '+inf'] else float(hi)
                        
                        result['bounds'][var] = {
                            'lower': lo_val,
                            'upper': hi_val
                        }
    
    return json.dumps(result, indent=2)