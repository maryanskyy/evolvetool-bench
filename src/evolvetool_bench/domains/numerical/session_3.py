"""Domain C, Session 3: Custom Optimization Format.

Key design principle: tasks use a PROPRIETARY optimization problem format (ARCOPT)
that no LLM can solve from training data. The agent MUST create and execute tools.

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (compute_stats, solve_linear, interpolate_1d)
  Gap 1:     Parse ARCOPT spec and extract the structured optimization problem
  Gap 2:     Solve the optimization problem (find minimum subject to constraints)
  Variant 1: Parse a different ARCOPT spec (different objective / constraint types)
  Variant 2: Solve a different optimization problem with more variables
  Compose 1: Parse + solve + compute stats on feasible region boundary points
  Regress 1: Re-parse an ARCOPT spec (same format, different coefficients)
  Adversarial 1: ARCOPT with infeasible constraints
  Adversarial 2: ARCOPT with unbounded objective (no lower bound)
"""

import json
import math
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── Proprietary format: ARCOPT ────────────────────────────────────────────────
#
# ARCOPT is a plain-text format for encoding single-objective numerical
# optimization problems with linear or quadratic objectives and linear
# inequality / equality constraints.
#
# Grammar (one line, semicolon-separated sections):
#
#   ARCOPT:v1;VARS:<x1>,<x2>,...;OBJ:<type>:<expr>;CONSTRS:<c1>|<c2>|...;BOUNDS:<b1>|<b2>|...
#
# VARS section:
#   Comma-separated variable names. The problem is minimization over these vars.
#
# OBJ section:
#   <type> is one of: "linear", "quadratic"
#   <expr> is a coefficient string:
#     linear:    "a1*x1+a2*x2+..."     (signed coefficients, no spaces)
#     quadratic: "a1*x1^2+a2*x2^2+a3*x1*x2+a4*x1+a5*x2+a6"
#       (all squared, cross, and linear terms, plus optional constant)
#
# CONSTRS section:
#   Pipe-separated constraints. Each constraint:
#     <lhs_expr> <op> <rhs>
#     where <op> is "<=", ">=", or "=="
#     <lhs_expr> uses same coefficient syntax as OBJ (linear only for constraints)
#   Example: "2*x1+3*x2<=12|x1+x2>=1"
#   If no constraints: CONSTRS:NONE
#
# BOUNDS section:
#   Pipe-separated variable bounds: "<var>:[<lo>,<hi>]"
#     Use "-inf" and "+inf" for unbounded sides.
#   Example: "x1:[0,+inf]|x2:[0,+inf]"
#   If no bounds: BOUNDS:NONE
#
# Gap 1 (parse): parse ARCOPT → return structured JSON:
#   {
#     "vars": ["x1", "x2"],
#     "objective": {"type": "linear"|"quadratic", "coeffs": {...}},
#     "constraints": [{"lhs": {...}, "op": "<="|">="|"==", "rhs": <float>}, ...],
#     "bounds": {"x1": [lo, hi], ...}   (null for ±inf)
#   }
#
# Gap 2 (solve): parse ARCOPT → call scipy.optimize.minimize or linprog →
#   return {"minimum": <float>, "at": {"x1": <float>, ...}}
#   Both values rounded to 6 decimal places.
#
# The agent must figure out the parsing logic and solve logic from the spec.

def _arcopt_encode(
    vars_: list[str],
    obj_type: str,
    obj_expr: str,
    constrs: list[str],
    bounds: list[str],
) -> str:
    """Encode an ARCOPT problem specification string."""
    constr_str = "|".join(constrs) if constrs else "NONE"
    bound_str = "|".join(bounds) if bounds else "NONE"
    return (
        f"ARCOPT:v1;VARS:{','.join(vars_)};"
        f"OBJ:{obj_type}:{obj_expr};"
        f"CONSTRS:{constr_str};"
        f"BOUNDS:{bound_str}"
    )


# ── Problem 1: Linear objective, linear constraints (2 vars) ─────────────────
# min  3*x1 + 2*x2
# s.t. x1 + x2 >= 4
#      2*x1 + x2 <= 14
#      x1 - x2 <= 3
#      x1 >= 0, x2 >= 0
# Solution: x1=0, x2=4 → minimum=8
ARCOPT_1 = _arcopt_encode(
    vars_=["x1", "x2"],
    obj_type="linear",
    obj_expr="3*x1+2*x2",
    constrs=["1*x1+1*x2>=4", "2*x1+1*x2<=14", "1*x1-1*x2<=3"],
    bounds=["x1:[0,+inf]", "x2:[0,+inf]"],
)
_PARSED_1 = {
    "vars": ["x1", "x2"],
    "objective": {"type": "linear", "coeffs": {"x1": 3.0, "x2": 2.0}},
    "constraints": [
        {"lhs": {"x1": 1.0, "x2": 1.0}, "op": ">=", "rhs": 4.0},
        {"lhs": {"x1": 2.0, "x2": 1.0}, "op": "<=", "rhs": 14.0},
        {"lhs": {"x1": 1.0, "x2": -1.0}, "op": "<=", "rhs": 3.0},
    ],
    "bounds": {"x1": [0.0, None], "x2": [0.0, None]},
}
_SOLVED_1 = {"minimum": 8.0, "at": {"x1": 0.0, "x2": 4.0}}


# ── Problem 2: Quadratic objective, linear constraints (2 vars) ──────────────
# min  (x1-2)^2 + (x2-3)^2  =  x1^2 + x2^2 - 4*x1 - 6*x2 + 13
# s.t. x1 + x2 <= 4
#      x1 >= 0, x2 >= 0
# Unconstrained min at (2,3), but x1+x2<=4 is satisfied (2+3=5 > 4), so
# constrained min on boundary x1+x2=4: KKT → x1=1.5, x2=2.5, f=0.5
ARCOPT_2 = _arcopt_encode(
    vars_=["x1", "x2"],
    obj_type="quadratic",
    obj_expr="1*x1^2+1*x2^2+-4*x1+-6*x2+13",
    constrs=["1*x1+1*x2<=4"],
    bounds=["x1:[0,+inf]", "x2:[0,+inf]"],
)
_PARSED_2 = {
    "vars": ["x1", "x2"],
    "objective": {
        "type": "quadratic",
        "coeffs": {"x1^2": 1.0, "x2^2": 1.0, "x1": -4.0, "x2": -6.0, "const": 13.0},
    },
    "constraints": [
        {"lhs": {"x1": 1.0, "x2": 1.0}, "op": "<=", "rhs": 4.0},
    ],
    "bounds": {"x1": [0.0, None], "x2": [0.0, None]},
}
_SOLVED_2 = {"minimum": 0.5, "at": {"x1": 1.5, "x2": 2.5}}


# ── Problem 3 (variant / regress): 3-variable linear ────────────────────────
# min  2*x1 + 5*x2 + 3*x3
# s.t. x1 + x2 + x3 >= 6
#      x1 + 2*x2 <= 10
#      x3 <= 4
#      x1,x2,x3 >= 0
# Solution: x3=4, x2=0, x1=2 → min=2*2+5*0+3*4=16
ARCOPT_3 = _arcopt_encode(
    vars_=["x1", "x2", "x3"],
    obj_type="linear",
    obj_expr="2*x1+5*x2+3*x3",
    constrs=["1*x1+1*x2+1*x3>=6", "1*x1+2*x2<=10", "1*x3<=4"],
    bounds=["x1:[0,+inf]", "x2:[0,+inf]", "x3:[0,+inf]"],
)
_PARSED_3 = {
    "vars": ["x1", "x2", "x3"],
    "objective": {"type": "linear", "coeffs": {"x1": 2.0, "x2": 5.0, "x3": 3.0}},
    "constraints": [
        {"lhs": {"x1": 1.0, "x2": 1.0, "x3": 1.0}, "op": ">=", "rhs": 6.0},
        {"lhs": {"x1": 1.0, "x2": 2.0}, "op": "<=", "rhs": 10.0},
        {"lhs": {"x3": 1.0}, "op": "<=", "rhs": 4.0},
    ],
    "bounds": {"x1": [0.0, None], "x2": [0.0, None], "x3": [0.0, None]},
}
_SOLVED_3 = {"minimum": 16.0, "at": {"x1": 2.0, "x2": 0.0, "x3": 4.0}}


# ── Adversarial 1: Infeasible constraint set ──────────────────────────────────
# min x1+x2   s.t.  x1>=3  AND  x1<=1  (impossible)
ARCOPT_INFEASIBLE = _arcopt_encode(
    vars_=["x1", "x2"],
    obj_type="linear",
    obj_expr="1*x1+1*x2",
    constrs=["1*x1>=3", "1*x1<=1"],
    bounds=["x1:[0,+inf]", "x2:[0,+inf]"],
)

# ── Adversarial 2: Unbounded objective ───────────────────────────────────────
# min -x1   with only x1<=10  (unbounded below for x1→-∞ because x1 has no lower bound)
ARCOPT_UNBOUNDED = _arcopt_encode(
    vars_=["x1"],
    obj_type="linear",
    obj_expr="-1*x1",
    constrs=["1*x1<=10"],
    bounds=["x1:[-inf,+inf]"],
)

# ── Regress data: fresh linear problem ────────────────────────────────────────
# min  4*x1 + x2
# s.t. x1 + x2 >= 3,  x1 <= 2,  x2 >= 0, x1 >= 0
# Solution: x1=0, x2=3 → min=3
ARCOPT_REGRESS = _arcopt_encode(
    vars_=["x1", "x2"],
    obj_type="linear",
    obj_expr="4*x1+1*x2",
    constrs=["1*x1+1*x2>=3", "1*x1<=2"],
    bounds=["x1:[0,+inf]", "x2:[0,+inf]"],
)
_SOLVED_REGRESS = {"minimum": 3.0, "at": {"x1": 0.0, "x2": 3.0}}


TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Solve this 2×2 linear system:\n"
            "  4x + y = 9\n"
            "  2x - 3y = 1\n\n"
            "Return x and y as floats."
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description=(
            "An optimization solver returns objective values at three iterations: "
            "[42.5, 31.2, 18.7]. Compute their mean, median, and std."
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "A constraint boundary passes through (0, 5) and (10, 0). "
            "Use linear interpolation to find the y value on this boundary when x = 4."
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks ────────────────────────────────────────────────
    Task(
        id="gap_1",
        description=(
            "Parse the following ARCOPT optimization problem specification.\n\n"
            "ARCOPT format:\n"
            "  ARCOPT:v1;VARS:<x1>,<x2>,...;OBJ:<type>:<expr>;"
            "CONSTRS:<c1>|<c2>|...;BOUNDS:<b1>|<b2>|...\n\n"
            "Sections:\n"
            "  VARS:   comma-separated variable names.\n"
            "  OBJ:    type is 'linear' or 'quadratic'; expr uses signed coefficients\n"
            "          e.g. '3*x1+2*x2' or '1*x1^2+1*x2^2+-4*x1+-6*x2+13'.\n"
            "          Quadratic terms: 'a*xi^2', cross terms: 'a*xi*xj',\n"
            "          linear terms: 'a*xi', constants: just a number.\n"
            "  CONSTRS: pipe-separated constraints. Each: '<lhs_expr> <op> <rhs>'\n"
            "           where op is '<=', '>=', or '=='.\n"
            "           If no constraints: CONSTRS:NONE.\n"
            "  BOUNDS: pipe-separated '<var>:[<lo>,<hi>]'. Use '-inf'/'+inf'.\n"
            "          If no bounds: BOUNDS:NONE.\n\n"
            f"Spec: {ARCOPT_1}\n\n"
            "Return a JSON object with keys: 'vars', 'objective' (with 'type' and 'coeffs'), "
            "'constraints' (list of {lhs, op, rhs}), and 'bounds' (null for ±inf)."
        ),
        task_type=TaskType.GAP,
        capability_id="arcopt_problem_parse",
        expected=_PARSED_1,
        hidden_tests=[
            # v1
            {"input": {"arcopt_spec": ARCOPT_2}, "expected": _PARSED_2},
            {"input": {"arcopt_spec": ARCOPT_3}, "expected": _PARSED_3},
            # v3 expansion (verify-style)
            {"input": {"arcopt_spec": ARCOPT_2},
             "verify": "isinstance(result, dict) and 'vars' in result and 'objective' in result"},
            {"input": {"arcopt_spec": ARCOPT_3},
             "verify": "isinstance(result, dict) and 'constraints' in result"},
            {"input": {"arcopt_spec": ARCOPT_1},
             "verify": "isinstance(result, dict) and isinstance(result.get('vars'), list)"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"arcopt_spec": "ARCOPT:v1;VARS:x1;OBJ:linear:0*x1;CONSTRS:NONE;BOUNDS:NONE"}},
            {"input": {"arcopt_spec": ARCOPT_INFEASIBLE}},
            {"input": {"arcopt_spec": ARCOPT_UNBOUNDED}},
            # v3 expansion
            {"input": {"arcopt_spec": ""}},
            {"input": {"arcopt_spec": "ARCOPT:v1;malformed"}},
            {"input": {"arcopt_spec": "completely garbage"}},
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Solve the following ARCOPT optimization problem — find the variable values "
            "that minimize the objective subject to the constraints.\n\n"
            "Use scipy.optimize.linprog for linear objectives or "
            "scipy.optimize.minimize (method='SLSQP') for quadratic.\n\n"
            f"Spec: {ARCOPT_1}\n\n"
            "Return a JSON object: {\"minimum\": <float>, \"at\": {\"x1\": <float>, ...}}\n"
            "Round all values to 6 decimal places."
        ),
        task_type=TaskType.GAP,
        capability_id="arcopt_optimize_solve",
        expected=_SOLVED_1,
        hidden_tests=[
            # v1
            {"input": {"arcopt_spec": ARCOPT_2}, "expected": _SOLVED_2},
            {"input": {"arcopt_spec": ARCOPT_REGRESS}, "expected": _SOLVED_REGRESS},
            # v3 expansion (verify-style for tolerance)
            {"input": {"arcopt_spec": ARCOPT_1},
             "verify": "isinstance(result, dict) and 'minimum' in result and 'at' in result"},
            {"input": {"arcopt_spec": ARCOPT_2},
             "verify": "isinstance(result, dict) and isinstance(result['minimum'], (int, float))"},
            {"input": {"arcopt_spec": ARCOPT_3},
             "verify": "isinstance(result, dict) and isinstance(result['at'], dict)"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"arcopt_spec": ARCOPT_INFEASIBLE}},
            {"input": {"arcopt_spec": ARCOPT_UNBOUNDED}},
            {"input": {"arcopt_spec": "ARCOPT:v1;VARS:x1;OBJ:linear:0*x1;CONSTRS:NONE;BOUNDS:x1:[5,5]"}},
            # v3 expansion
            {"input": {"arcopt_spec": ""}},
            {"input": {"arcopt_spec": "completely garbage spec"}},
            {"input": {"arcopt_spec": "ARCOPT:v1;VARS:;OBJ:linear:;CONSTRS:NONE;BOUNDS:NONE"}},  # no vars
        ],
    ),

    # ── Variant tasks ─────────────────────────────────────────────
    Task(
        id="variant_1",
        description=(
            "Parse this ARCOPT problem specification. Same format as before.\n\n"
            f"Spec: {ARCOPT_2}\n\n"
            "Return the structured JSON representation."
        ),
        task_type=TaskType.VARIANT,
        capability_id="arcopt_problem_parse",
        reuses_task="gap_1",
        expected=_PARSED_2,
    ),
    Task(
        id="variant_2",
        description=(
            "Solve this ARCOPT optimization problem. Same format as before.\n\n"
            f"Spec: {ARCOPT_3}\n\n"
            "Return {\"minimum\": ..., \"at\": {...}} rounded to 6 dp."
        ),
        task_type=TaskType.VARIANT,
        capability_id="arcopt_optimize_solve",
        reuses_task="gap_2",
        expected=_SOLVED_3,
    ),

    # ── Compose task ──────────────────────────────────────────────
    Task(
        id="compose_1",
        description=(
            "Parse and solve this ARCOPT problem. Then sample 5 evenly spaced points "
            "along the active constraint boundary (x1+x2=4, x1 in [0,2]) and compute "
            "statistics (mean, median, std) of the objective values at those points.\n\n"
            f"Spec: {ARCOPT_2}\n\n"
            "Return a JSON object with keys:\n"
            "  'solution': {\"minimum\": ..., \"at\": {...}}\n"
            "  'boundary_points': list of (x1,x2) pairs\n"
            "  'boundary_obj_values': list of objective values at those points\n"
            "  'stats': {mean, median, std} of boundary objective values"
        ),
        task_type=TaskType.COMPOSE,
        capability_id="arcopt_parse_solve_boundary_stats",
        composes_tasks=["gap_1", "gap_2", "seed_2"],
    ),

    # ── Regress task ──────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            "Parse this ARCOPT problem (same format as before):\n\n"
            f"Spec: {ARCOPT_REGRESS}\n\n"
            "Return the structured JSON representation."
        ),
        task_type=TaskType.REGRESS,
        capability_id="arcopt_problem_parse",
        reuses_task="gap_1",
        expected={
            "vars": ["x1", "x2"],
            "objective": {"type": "linear", "coeffs": {"x1": 4.0, "x2": 1.0}},
            "constraints": [
                {"lhs": {"x1": 1.0, "x2": 1.0}, "op": ">=", "rhs": 3.0},
                {"lhs": {"x1": 1.0}, "op": "<=", "rhs": 2.0},
            ],
            "bounds": {"x1": [0.0, None], "x2": [0.0, None]},
        },
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Attempt to solve this ARCOPT problem. WARNING: the constraints are "
            "mutually infeasible — no point satisfies all of them simultaneously. "
            "Your solver tool must detect this and return a graceful error response "
            "rather than crashing or returning a nonsensical result.\n\n"
            f"Spec: {ARCOPT_INFEASIBLE}\n\n"
            "Return a JSON object with key 'error' explaining the infeasibility, "
            "e.g. {\"error\": \"infeasible\", \"detail\": \"...\"}"
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="arcopt_optimize_solve",
        breaks_task="gap_2",
    ),
    Task(
        id="adversarial_2",
        description=(
            "Attempt to solve this ARCOPT problem. WARNING: the objective is unbounded "
            "below (no finite minimum exists) because the variable has no lower bound. "
            "Your solver tool must detect and report this rather than running forever "
            "or returning an extreme value.\n\n"
            f"Spec: {ARCOPT_UNBOUNDED}\n\n"
            "Return a JSON object with key 'error' describing the unboundedness, "
            "e.g. {\"error\": \"unbounded\", \"detail\": \"...\"}"
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="arcopt_optimize_solve",
        breaks_task="gap_2",
    ),
]


def create_session() -> Session:
    return Session(
        id="numerical_s3",
        name="Custom Optimization Format (ARCOPT)",
        domain="numerical",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description=(
            "Tests tool creation for a proprietary optimization problem format (ARCOPT). "
            "Gap tasks require parsing coefficient expressions, setting up scipy LP/QP "
            "solvers, and handling degenerate cases (infeasible, unbounded). "
            "Cannot be solved from training data."
        ),
    )
