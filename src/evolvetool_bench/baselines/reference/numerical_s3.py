"""Hand-crafted reference implementations for numerical session 3 gap tasks.

These prove the held-out conformance suites (hidden_tests) are passable by a
correct implementation. Each entry's ``implementation`` is a self-contained
Python source string executed in a bare subprocess by the tool-quality
evaluator (stdlib only — no scipy assumed); the function is called with
**input kwargs and its return value is JSON-round-tripped before comparison,
so outputs use only JSON-safe types and contain exactly the expected keys.

The solver avoids scipy by exact enumeration: LP minima lie at vertices
(intersections of n active constraint hyperplanes), and convex QP minima are
KKT points of some active set — both solvable exactly via Gaussian
elimination, so values round cleanly to the expected 6-decimal answers.
"""

ARCOPT_PARSE_IMPL = '''\
def arcopt_parse(arcopt_spec: str) -> dict:
    """Parse an ARCOPT v1 optimization spec into its structured JSON form.

    Returns {'vars', 'objective': {'type', 'coeffs'}, 'constraints': [{lhs, op, rhs}],
    'bounds': {var: [lo, hi]}} with None for +/-inf bound sides.
    On malformed input returns {'error': str} instead of raising.
    """
    def parse_terms(expr: str) -> dict:
        coeffs = {}
        for term in expr.replace("-", "+-").split("+"):
            term = term.strip()
            if not term or term == "-":
                continue
            if "*" in term:
                coeff_str, key = term.split("*", 1)
                coeffs[key] = coeffs.get(key, 0.0) + float(coeff_str)
            else:
                coeffs["const"] = coeffs.get("const", 0.0) + float(term)
        return coeffs

    try:
        if not isinstance(arcopt_spec, str) or not arcopt_spec.startswith("ARCOPT:v1;"):
            return {"error": "not a valid ARCOPT v1 spec"}
        sections = {}
        for part in arcopt_spec.split(";")[1:]:
            head, _, body = part.partition(":")
            sections[head] = body
        vars_ = [v for v in sections.get("VARS", "").split(",") if v]
        obj_type, _, obj_expr = sections.get("OBJ", "").partition(":")
        objective = {"type": obj_type, "coeffs": parse_terms(obj_expr)}
        constraints = []
        constr_body = sections.get("CONSTRS", "NONE")
        if constr_body and constr_body != "NONE":
            for constr in constr_body.split("|"):
                for op in ("<=", ">=", "=="):
                    if op in constr:
                        lhs_expr, rhs_str = constr.split(op)
                        constraints.append(
                            {"lhs": parse_terms(lhs_expr), "op": op, "rhs": float(rhs_str)}
                        )
                        break
        bounds = {}
        bound_body = sections.get("BOUNDS", "NONE")
        if bound_body and bound_body != "NONE":
            for bound in bound_body.split("|"):
                var, _, rng = bound.partition(":")
                lo_str, hi_str = rng.strip("[]").split(",")
                bounds[var] = [
                    None if "inf" in lo_str else float(lo_str),
                    None if "inf" in hi_str else float(hi_str),
                ]
        return {"vars": vars_, "objective": objective,
                "constraints": constraints, "bounds": bounds}
    except Exception as exc:
        return {"error": "parse failure: %s" % exc}
'''

ARCOPT_SOLVE_IMPL = '''\
def arcopt_solve(arcopt_spec: str) -> dict:
    """Solve an ARCOPT v1 minimization problem exactly (LP vertex / QP KKT enumeration).

    Returns {'minimum': float, 'at': {var: float}} rounded to 6 decimal places.
    Infeasible/unbounded/malformed specs yield {'error': str} instead of raising.
    """
    from itertools import combinations

    def parse_terms(expr: str) -> dict:
        coeffs = {}
        for term in expr.replace("-", "+-").split("+"):
            term = term.strip()
            if not term or term == "-":
                continue
            if "*" in term:
                coeff_str, key = term.split("*", 1)
                coeffs[key] = coeffs.get(key, 0.0) + float(coeff_str)
            else:
                coeffs["const"] = coeffs.get("const", 0.0) + float(term)
        return coeffs

    def lin_solve(rows_aug):
        m = [row[:] for row in rows_aug]
        k = len(m)
        for col in range(k):
            piv = max(range(col, k), key=lambda r: abs(m[r][col]))
            if abs(m[piv][col]) < 1e-10:
                return None
            m[col], m[piv] = m[piv], m[col]
            for r in range(k):
                if r != col and m[r][col] != 0.0:
                    factor = m[r][col] / m[col][col]
                    for j in range(col, k + 1):
                        m[r][j] -= factor * m[col][j]
        return [m[r][k] / m[r][r] for r in range(k)]

    try:
        if not isinstance(arcopt_spec, str) or not arcopt_spec.startswith("ARCOPT:v1;"):
            return {"error": "not a valid ARCOPT v1 spec"}
        sections = {}
        for part in arcopt_spec.split(";")[1:]:
            head, _, body = part.partition(":")
            sections[head] = body
        vars_ = [v for v in sections.get("VARS", "").split(",") if v]
        if not vars_:
            return {"error": "no variables declared"}
        n = len(vars_)
        idx = {v: i for i, v in enumerate(vars_)}
        obj_type, _, obj_expr = sections.get("OBJ", "").partition(":")
        obj = parse_terms(obj_expr)

        def f(x):
            total = 0.0
            for key, a in obj.items():
                if key == "const":
                    total += a
                elif key.endswith("^2"):
                    total += a * x[idx[key[:-2]]] ** 2
                elif "*" in key:
                    u, w = key.split("*")
                    total += a * x[idx[u]] * x[idx[w]]
                else:
                    total += a * x[idx[key]]
            return total

        big = 1e8
        rows = []  # (a_vec, op, rhs, is_artificial)
        constr_body = sections.get("CONSTRS", "NONE")
        if constr_body and constr_body != "NONE":
            for constr in constr_body.split("|"):
                for op in ("<=", ">=", "=="):
                    if op in constr:
                        lhs_expr, rhs_str = constr.split(op)
                        a = [0.0] * n
                        for key, val in parse_terms(lhs_expr).items():
                            if key != "const":
                                a[idx[key]] += val
                        rows.append((a, op, float(rhs_str), False))
                        break
        bounds = {}
        bound_body = sections.get("BOUNDS", "NONE")
        if bound_body and bound_body != "NONE":
            for bound in bound_body.split("|"):
                var, _, rng = bound.partition(":")
                lo_str, hi_str = rng.strip("[]").split(",")
                bounds[var] = (None if "inf" in lo_str else float(lo_str),
                               None if "inf" in hi_str else float(hi_str))
        for v in vars_:
            lo, hi = bounds.get(v, (None, None))
            e = [1.0 if u == v else 0.0 for u in vars_]
            rows.append((e, ">=", -big if lo is None else lo, lo is None))
            rows.append((e, "<=", big if hi is None else hi, hi is None))

        tol = 1e-6

        def feasible(x):
            for a, op, b, _ in rows:
                val = sum(ai * xi for ai, xi in zip(a, x))
                if op == "<=" and val > b + tol:
                    return False
                if op == ">=" and val < b - tol:
                    return False
                if op == "==" and abs(val - b) > tol:
                    return False
            return True

        candidates = []  # (f value, uses_artificial_active_row, x)
        if obj_type == "quadratic":
            q = [[0.0] * n for _ in range(n)]
            c = [0.0] * n
            for key, a in obj.items():
                if key == "const":
                    continue
                elif key.endswith("^2"):
                    i = idx[key[:-2]]
                    q[i][i] += a
                elif "*" in key:
                    u, w = key.split("*")
                    q[idx[u]][idx[w]] += a / 2.0
                    q[idx[w]][idx[u]] += a / 2.0
                else:
                    c[idx[key]] += a
            for size in range(n + 1):
                for active in combinations(range(len(rows)), size):
                    k = n + size
                    aug = []
                    for i in range(n):
                        row = [2.0 * q[i][j] for j in range(n)]
                        row += [rows[r][0][i] for r in active] + [-c[i]]
                        aug.append(row)
                    for r in active:
                        aug.append(rows[r][0][:] + [0.0] * size + [rows[r][2]])
                    sol = lin_solve(aug)
                    if sol is not None and feasible(sol[:n]):
                        art = any(rows[r][3] for r in active)
                        candidates.append((f(sol[:n]), art, sol[:n]))
        else:
            for active in combinations(range(len(rows)), n):
                aug = [rows[r][0][:] + [rows[r][2]] for r in active]
                sol = lin_solve(aug)
                if sol is not None and feasible(sol):
                    candidates.append((f(sol), any(rows[r][3] for r in active), sol))

        if not candidates:
            return {"error": "infeasible", "detail": "no point satisfies all constraints"}
        best = min(candidates, key=lambda cand: (cand[0], cand[1]))
        if best[1]:
            return {"error": "unbounded", "detail": "optimum escapes to infinity"}
        return {"minimum": round(best[0], 6) + 0.0,
                "at": {v: round(best[2][i], 6) + 0.0 for i, v in enumerate(vars_)}}
    except Exception as exc:
        return {"error": "solve failure: %s" % exc}
'''


REFERENCE_IMPLS = {
    "arcopt_problem_parse": {
        "session_id": "numerical_s3",
        "task_id": "gap_1",
        "name": "arcopt_parse",
        "implementation": ARCOPT_PARSE_IMPL,
    },
    "arcopt_optimize_solve": {
        "session_id": "numerical_s3",
        "task_id": "gap_2",
        "name": "arcopt_solve",
        "implementation": ARCOPT_SOLVE_IMPL,
    },
}
