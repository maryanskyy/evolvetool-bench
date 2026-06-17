"""Domain C, Session 1: Custom Curve Fitting.

Key design principle: tasks use a PROPRIETARY model-specification format (ARCFIT)
that no LLM can solve from training data. The agent MUST create and execute tools.

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (compute_stats, solve_linear, interpolate_1d)
  Gap 1:     Parse ARCFIT spec and fit model parameters to data (least-squares)
  Gap 2:     Evaluate a fitted ARCFIT model on new x values
  Variant 1: Fit a different ARCFIT model (power_law) with different data
  Variant 2: Evaluate a fitted model with more query points
  Compose 1: Fit model → evaluate on new points → return stats of predicted y values
  Regress 1: Re-fit same model type with fresh data set
  Adversarial 1: ARCFIT with noisy / near-degenerate data
  Adversarial 2: Evaluate model at edge-case x values (0, negative, very large)
"""

import math
import json
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── Proprietary format: ARCFIT ────────────────────────────────────────────────
#
# ARCFIT is a single-line text format that encodes a named parametric model
# together with training data and free-parameter markers.
#
# Grammar:
#   MODEL:<name>;PARAMS:<key>=<val_or_?>,...;DATA:<x1>,<y1>|<x2>,<y2>|...
#
# Supported models (the agent must discover how to fit them from the spec alone):
#   exp_decay  : y = a * exp(-b * x) + c
#   power_law  : y = a * x^b + c           (x > 0 assumed)
#   logistic   : y = L / (1 + exp(-k*(x-x0)))   params: L=?,k=?,x0=?
#
# A "?" value means the parameter is free and must be fitted.
# A numeric value means the parameter is fixed (not fitted).
#
# Fitting method: non-linear least-squares via scipy.optimize.curve_fit
# (agents must figure out the mapping from model name → formula → fitting).
#
# Evaluation format:
#   FITTED:<name>;PARAMS:<key>=<fitted_val>,...;QUERY:<x1>,<x2>,...
# Returns JSON list of predicted y values rounded to 6 decimal places.

def _arcfit_encode(model: str, params: dict, data_xy: list[tuple[float, float]]) -> str:
    """Encode an ARCFIT model-spec string."""
    param_str = ",".join(
        f"{k}={'?' if v is None else v}" for k, v in params.items()
    )
    data_str = "|".join(f"{x},{y}" for x, y in data_xy)
    return f"MODEL:{model};PARAMS:{param_str};DATA:{data_str}"


def _arcfit_eval_encode(model: str, fitted_params: dict, query_xs: list[float]) -> str:
    """Encode an ARCFIT evaluation request."""
    param_str = ",".join(f"{k}={v}" for k, v in fitted_params.items())
    query_str = ",".join(str(x) for x in query_xs)
    return f"FITTED:{model};PARAMS:{param_str};QUERY:{query_str}"


def _exp_decay(x: float, a: float, b: float, c: float) -> float:
    return a * math.exp(-b * x) + c


def _power_law(x: float, a: float, b: float, c: float) -> float:
    return a * (x ** b) + c


def _logistic(x: float, L: float, k: float, x0: float) -> float:
    return L / (1.0 + math.exp(-k * (x - x0)))


# ── Generate training data ────────────────────────────────────────────────────
# exp_decay: a=3.0, b=0.5, c=1.0  →  y = 3*exp(-0.5*x) + 1
_EXP_TRUE = {"a": 3.0, "b": 0.5, "c": 1.0}
_EXP_DATA = [(float(x), round(_exp_decay(x, **_EXP_TRUE), 6)) for x in [0, 1, 2, 3, 4, 5, 6]]

# power_law: a=2.0, b=0.5, c=0.5  →  y = 2*x^0.5 + 0.5
_POW_TRUE = {"a": 2.0, "b": 0.5, "c": 0.5}
_POW_DATA = [(float(x), round(_power_law(x, **_POW_TRUE), 6)) for x in [1, 2, 4, 9, 16, 25]]

# logistic: L=10.0, k=1.0, x0=5.0
_LOG_TRUE = {"L": 10.0, "k": 1.0, "x0": 5.0}
_LOG_DATA = [(float(x), round(_logistic(x, **_LOG_TRUE), 6)) for x in [0, 2, 4, 5, 6, 8, 10]]

# regression / fresh data: exp_decay with a=5.0, b=0.3, c=0.5
_EXP2_TRUE = {"a": 5.0, "b": 0.3, "c": 0.5}
_EXP2_DATA = [(float(x), round(_exp_decay(x, **_EXP2_TRUE), 6)) for x in [0, 1, 2, 3, 5, 8, 10]]

# adversarial: very noisy / near-zero slope (hard to fit)
import random as _random
_random.seed(42)
_ADV_TRUE = {"a": 0.01, "b": 2.0, "c": 100.0}  # tiny a, dominantly flat
_ADV_DATA = [
    (float(x), round(_exp_decay(x, **_ADV_TRUE) + _random.uniform(-0.001, 0.001), 8))
    for x in [0, 1, 2, 3, 4, 5]
]

# ── Encode the ARCFIT strings ─────────────────────────────────────────────────
ARCFIT_EXP = _arcfit_encode("exp_decay", {"a": None, "b": None, "c": None}, _EXP_DATA)
ARCFIT_POW = _arcfit_encode("power_law", {"a": None, "b": None, "c": None}, _POW_DATA)
ARCFIT_LOG = _arcfit_encode("logistic", {"L": None, "k": None, "x0": None}, _LOG_DATA)
ARCFIT_EXP2 = _arcfit_encode("exp_decay", {"a": None, "b": None, "c": None}, _EXP2_DATA)
ARCFIT_ADV = _arcfit_encode("exp_decay", {"a": None, "b": None, "c": None}, _ADV_DATA)

# Fitted evaluation strings (gap_2 tasks)
# These use true params — evaluation only, no fitting required.
ARCFIT_EVAL_EXP = _arcfit_eval_encode(
    "exp_decay", {"a": 3.0, "b": 0.5, "c": 1.0}, [0.5, 1.5, 2.5, 7.0]
)
ARCFIT_EVAL_POW = _arcfit_eval_encode(
    "power_law", {"a": 2.0, "b": 0.5, "c": 0.5}, [36.0, 49.0, 64.0, 100.0]
)
ARCFIT_EVAL_EDGE = _arcfit_eval_encode(
    "exp_decay", {"a": 1.0, "b": 1.0, "c": 0.0}, [0.0, -1.0, 100.0]
)

# Expected evaluation outputs
_EVAL_EXP_EXPECTED = [round(_exp_decay(x, 3.0, 0.5, 1.0), 6) for x in [0.5, 1.5, 2.5, 7.0]]
_EVAL_POW_EXPECTED = [round(_power_law(x, 2.0, 0.5, 0.5), 6) for x in [36.0, 49.0, 64.0, 100.0]]
_EVAL_EDGE_EXPECTED = [round(_exp_decay(x, 1.0, 1.0, 0.0), 6) for x in [0.0, -1.0, 100.0]]


TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Compute statistics for this dataset:\n"
            "[4.2, 7.8, 3.1, 9.5, 2.6, 6.4, 8.3, 1.9, 5.7, 4.8]\n\n"
            "Return mean, median, and population standard deviation."
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description=(
            "Solve this 2×2 linear system for [x, y]:\n"
            "  2x + 3y = 8\n"
            "  5x -  y = 1\n\n"
            "Return x and y as floats."
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "A sensor reads 14.7 at t=2.0 and 31.3 at t=6.0. "
            "Use linear interpolation to estimate the value at t=3.5."
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks (require creating new tools) ───────────────────
    Task(
        id="gap_1",
        description=(
            "Parse and fit the following ARCFIT model specification.\n\n"
            "ARCFIT is a proprietary curve-fitting format:\n"
            "  MODEL:<name>;PARAMS:<key>=<val_or_?>,...;DATA:<x1>,<y1>|<x2>,<y2>|...\n\n"
            "Supported models:\n"
            "  exp_decay : y = a * exp(-b * x) + c\n"
            "  power_law : y = a * x^b + c\n"
            "  logistic  : y = L / (1 + exp(-k*(x - x0)))\n\n"
            "Parameters marked '?' are free and must be fitted to the DATA using "
            "non-linear least squares. Fixed numeric parameters must not be changed.\n\n"
            f"Spec: {ARCFIT_EXP}\n\n"
            "Return a JSON object mapping each parameter name to its fitted value, "
            "rounded to 6 decimal places."
        ),
        task_type=TaskType.GAP,
        capability_id="arcfit_curve_fit",
        expected={"a": round(_EXP_TRUE["a"], 6), "b": round(_EXP_TRUE["b"], 6), "c": round(_EXP_TRUE["c"], 6)},
        hidden_tests=[
            # v1
            {"input": {"arcfit_spec": ARCFIT_POW},
             "expected": {k: round(v, 6) for k, v in _POW_TRUE.items()}},
            {"input": {"arcfit_spec": ARCFIT_LOG},
             "expected": {k: round(v, 6) for k, v in _LOG_TRUE.items()}},
            # v3 expansion: verify-style checks for tolerance to fit precision
            {"input": {"arcfit_spec": ARCFIT_POW},
             "verify": "isinstance(result, dict) and all(k in result for k in ('a','b','c'))"},
            {"input": {"arcfit_spec": ARCFIT_LOG},
             "verify": "isinstance(result, dict) and any(k in result for k in ('L','k','x0'))"},
            {"input": {"arcfit_spec": ARCFIT_POW},
             "verify": "isinstance(result, dict) and abs(result.get('b', 0) - " + str(round(_POW_TRUE['b'], 1)) + ") < 2.0"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"arcfit_spec": "MODEL:exp_decay;PARAMS:a=?,b=?,c=?;DATA:"}},
            {"input": {"arcfit_spec": "MODEL:exp_decay;PARAMS:a=?,b=?,c=?;DATA:0,1"}},
            {"input": {"arcfit_spec": ARCFIT_ADV}},
            # v3 expansion
            {"input": {"arcfit_spec": "MODEL:unknown_model;PARAMS:a=?;DATA:1,2;2,3"}},
            {"input": {"arcfit_spec": "completely garbage input"}},
            {"input": {"arcfit_spec": "MODEL:exp_decay;PARAMS:a=?,b=?,c=?;DATA:0,nan"}},
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Evaluate a previously fitted ARCFIT model on new x values.\n\n"
            "The evaluation format is:\n"
            "  FITTED:<name>;PARAMS:<key>=<fitted_val>,...;QUERY:<x1>,<x2>,...\n\n"
            "Apply the named model formula with the given parameters to each QUERY x.\n\n"
            f"Spec: {ARCFIT_EVAL_EXP}\n\n"
            "Return a JSON list of predicted y values, each rounded to 6 decimal places."
        ),
        task_type=TaskType.GAP,
        capability_id="arcfit_model_evaluate",
        expected=_EVAL_EXP_EXPECTED,
        hidden_tests=[
            # v1
            {"input": {"eval_spec": ARCFIT_EVAL_POW}, "expected": _EVAL_POW_EXPECTED},
            {"input": {"eval_spec": _arcfit_eval_encode(
                "logistic", {"L": 10.0, "k": 1.0, "x0": 5.0}, [3.0, 5.0, 7.0])},
             "expected": [round(_logistic(x, 10.0, 1.0, 5.0), 6) for x in [3.0, 5.0, 7.0]]},
            # v3 expansion
            {"input": {"eval_spec": _arcfit_eval_encode(
                "logistic", {"L": 1.0, "k": 1.0, "x0": 0.0}, [-5.0, 0.0, 5.0])},
             "verify": "isinstance(result, list) and len(result) == 3 and abs(result[1] - 0.5) < 0.01"},
            {"input": {"eval_spec": _arcfit_eval_encode(
                "exp_decay", {"a": 2.0, "b": 1.0, "c": 0.0}, [0.0])},
             "verify": "isinstance(result, list) and abs(result[0] - 2.0) < 0.01"},
            {"input": {"eval_spec": _arcfit_eval_encode(
                "power_law", {"a": 1.0, "b": 2.0, "c": 0.0}, [2.0, 3.0])},
             "verify": "isinstance(result, list) and abs(result[0] - 4.0) < 0.01 and abs(result[1] - 9.0) < 0.01"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"eval_spec": ARCFIT_EVAL_EDGE}},
            {"input": {"eval_spec": _arcfit_eval_encode("power_law", {"a": 1.0, "b": 0.5, "c": 0.0}, [0.0001])}},
            {"input": {"eval_spec": _arcfit_eval_encode("exp_decay", {"a": 1e6, "b": 0.001, "c": 0.0}, [1000.0])}},
            # v3 expansion
            {"input": {"eval_spec": "FITTED:unknown;PARAMS:a=1.0;QUERY:1.0"}},
            {"input": {"eval_spec": ""}},
            {"input": {"eval_spec": "FITTED:exp_decay;PARAMS:a=nan;QUERY:1.0"}},
        ],
    ),

    # ── Variant tasks (should REUSE gap tools) ───────────────────
    Task(
        id="variant_1",
        description=(
            "Fit an ARCFIT model specification. Same format as before.\n\n"
            f"Spec: {ARCFIT_POW}\n\n"
            "Return a JSON object with fitted parameter values (rounded to 6 dp)."
        ),
        task_type=TaskType.VARIANT,
        capability_id="arcfit_curve_fit",
        reuses_task="gap_1",
        expected={k: round(v, 6) for k, v in _POW_TRUE.items()},
    ),
    Task(
        id="variant_2",
        description=(
            "Evaluate an ARCFIT fitted model on query points. Same format as before.\n\n"
            f"Spec: {ARCFIT_EVAL_POW}\n\n"
            "Return a JSON list of predicted y values (rounded to 6 dp)."
        ),
        task_type=TaskType.VARIANT,
        capability_id="arcfit_model_evaluate",
        reuses_task="gap_2",
        expected=_EVAL_POW_EXPECTED,
    ),

    # ── Compose task (chain gap_1 → gap_2 → seed stats) ─────────
    Task(
        id="compose_1",
        description=(
            "Fit the ARCFIT model, then evaluate it on x = [0, 2, 4, 6, 8, 10], "
            "then compute statistics (mean, median, std) of the predicted y values.\n\n"
            f"Spec: {ARCFIT_EXP}\n\n"
            "Return a JSON object with keys 'fitted_params', 'predictions', and 'stats'."
        ),
        task_type=TaskType.COMPOSE,
        capability_id="arcfit_fit_evaluate_stats",
        composes_tasks=["gap_1", "gap_2", "seed_1"],
    ),

    # ── Regress task ──────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            "Fit the ARCFIT model below (same format as before):\n\n"
            f"Spec: {ARCFIT_EXP2}\n\n"
            "Return a JSON object with fitted parameter values (rounded to 6 dp)."
        ),
        task_type=TaskType.REGRESS,
        capability_id="arcfit_curve_fit",
        reuses_task="gap_1",
        expected={k: round(v, 6) for k, v in _EXP2_TRUE.items()},
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Fit this ARCFIT spec. WARNING: the data has significant measurement noise "
            "and the exponential signal amplitude is very small relative to the offset. "
            "Your fitting tool must handle near-degenerate cases without crashing.\n\n"
            f"Spec: {ARCFIT_ADV}\n\n"
            "Return the fitted parameters as a JSON object (6 dp). "
            "Accept any result where c ≈ 100.0 (±0.5) since a and b are poorly constrained."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="arcfit_curve_fit",
        breaks_task="gap_1",
    ),
    Task(
        id="adversarial_2",
        description=(
            "Evaluate this ARCFIT model at edge-case x values including 0, negatives, "
            "and extremely large x. Your evaluation tool must not crash or produce NaN.\n\n"
            f"Spec: {ARCFIT_EVAL_EDGE}\n\n"
            "Return a JSON list of predicted y values (rounded to 6 dp). "
            "For x=100 the result should be effectively 0 (exp underflow is fine, treat as 0)."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="arcfit_model_evaluate",
        breaks_task="gap_2",
        expected=_EVAL_EDGE_EXPECTED,
    ),
]


def create_session() -> Session:
    return Session(
        id="numerical_s1",
        name="Custom Curve Fitting (ARCFIT format)",
        domain="numerical",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description=(
            "Tests tool creation for a proprietary curve-fitting format (ARCFIT). "
            "Gap tasks require parsing the spec, fitting model parameters with scipy, "
            "and evaluating models on new inputs. Cannot be solved from training data."
        ),
    )
