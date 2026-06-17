"""Hand-crafted reference implementations for numerical sessions 1 and 2.

These implementations exist to prove that the held-out conformance suites
(``hidden_tests``) for each gap-task capability are passable by a correct
implementation. They are evaluated with
``evolvetool_bench.evaluation.tool_quality.evaluate_tool`` exactly like
agent-synthesized tools (exec'd in a bare subprocess, called with the
hidden-test input kwargs, compared against ``expected`` / ``verify``).

Notes on deliberate choices:

* ``arcfit_curve_fit`` uses ``scipy.optimize.curve_fit`` with tight
  tolerances and multi-start initial guesses so the fitted parameters round
  exactly to the ground-truth values at 6 decimal places (the hidden tests
  use exact equality on the rounded values).
* ``arcsig_fft_spectrum`` reproduces the session's reference brute-force DFT
  expression *verbatim* so the floating-point sums are bitwise identical to
  the precomputed expected spectra before rounding.
* ``arcsig_bandpass_filter`` emits ``ENC=f32le_b64`` (equals sign) in the
  output header because both the gap_2 task description and the hidden-test
  verify expression use that exact substring; the decoder accepts both the
  ``:`` and ``=`` field separators.
* All four functions return an ``{"error": ...}`` dict on malformed input
  instead of raising, for graceful adversarial-test handling.
"""

ARCFIT_CURVE_FIT_IMPL = '''def arcfit_curve_fit(arcfit_spec: str) -> dict:
    """Parse an ARCFIT spec and fit its free parameters by least squares.

    Spec grammar: MODEL:<name>;PARAMS:<key>=<val_or_?>,...;DATA:<x,y>|...
    Parameters marked '?' are fitted; numeric parameters stay fixed.
    Returns {param: fitted_value rounded to 6 dp} or {"error": ...}.
    """
    try:
        import numpy as np
        from scipy.optimize import curve_fit
        fields = dict(p.split(":", 1) for p in arcfit_spec.strip().split(";") if ":" in p)
        model = fields["MODEL"]
        items = [p.split("=", 1) for p in fields["PARAMS"].split(",") if "=" in p]
        names = [k for k, _ in items]
        fixed = {k: float(v) for k, v in items if v != "?"}
        free = [k for k, v in items if v == "?"]
        pts = [p.split(",", 1) for p in fields.get("DATA", "").split("|") if "," in p]
        xs = np.array([float(a) for a, _ in pts], dtype=float)
        ys = np.array([float(b) for _, b in pts], dtype=float)
        if len(xs) < max(len(free), 1):
            return {"error": "not enough data points to fit"}
        formulas = {
            "exp_decay": (("a", "b", "c"), lambda x, a, b, c: a * np.exp(-b * x) + c),
            "power_law": (("a", "b", "c"), lambda x, a, b, c: a * np.power(x, b) + c),
            "logistic": (("L", "k", "x0"), lambda x, L, k, x0: L / (1.0 + np.exp(-k * (x - x0)))),
        }
        if model not in formulas:
            return {"error": "unknown model: " + model}
        order, fn = formulas[model]

        def wrapper(x, *free_vals):
            vals = dict(fixed)
            vals.update(zip(free, free_vals))
            return fn(x, *[vals[k] for k in order])

        lo, hi = float(ys.min()), float(ys.max())
        mid_x = float(xs[int(np.argmin(np.abs(ys - (lo + hi) / 2.0)))])
        guesses = [
            {"a": hi - lo or 1.0, "b": 1.0, "c": lo, "L": hi or 1.0, "k": 1.0, "x0": mid_x},
            {"a": 1.0, "b": 0.5, "c": 0.0, "L": 1.0, "k": 0.5, "x0": float(np.median(xs))},
            {"a": hi or 1.0, "b": 0.1, "c": 0.0, "L": 2.0 * hi or 1.0, "k": 2.0, "x0": mid_x},
        ]
        best = None
        for g in guesses:
            try:
                popt, _ = curve_fit(
                    wrapper, xs, ys, p0=[g.get(k, 1.0) for k in free],
                    maxfev=20000, ftol=1e-15, xtol=1e-15, gtol=1e-15,
                )
                sse = float(np.sum((np.asarray(wrapper(xs, *popt), dtype=float) - ys) ** 2))
                if np.isfinite(sse) and (best is None or sse < best[0]):
                    best = (sse, popt)
            except Exception:
                continue
        if best is None:
            return {"error": "fit did not converge"}
        fitted = dict(fixed)
        fitted.update(zip(free, (float(v) for v in best[1])))
        return {k: round(float(fitted[k]), 6) for k in names}
    except Exception as e:
        return {"error": str(e)}
'''


ARCFIT_MODEL_EVALUATE_IMPL = '''def arcfit_model_evaluate(eval_spec: str) -> list:
    """Evaluate a fitted ARCFIT model on query x values.

    Spec grammar: FITTED:<name>;PARAMS:<key>=<val>,...;QUERY:<x1>,<x2>,...
    Returns predicted y values rounded to 6 dp (None for unevaluable points),
    or {"error": ...} on malformed input.
    """
    import math
    try:
        fields = dict(p.split(":", 1) for p in eval_spec.strip().split(";") if ":" in p)
        model = fields["FITTED"]
        params = {k: float(v) for k, v in
                  (p.split("=", 1) for p in fields["PARAMS"].split(",") if "=" in p)}
        xs = [float(x) for x in fields["QUERY"].split(",") if x.strip()]

        def safe_exp(v: float) -> float:
            try:
                return math.exp(v)
            except OverflowError:
                return float("inf")

        formulas = {
            "exp_decay": lambda x: params["a"] * safe_exp(-params["b"] * x) + params["c"],
            "power_law": lambda x: params["a"] * (x ** params["b"]) + params["c"],
            "logistic": lambda x: params["L"] / (1.0 + safe_exp(-params["k"] * (x - params["x0"]))),
        }
        if model not in formulas:
            return {"error": "unknown model: " + model}
        ys = []
        for x in xs:
            try:
                ys.append(round(float(formulas[model](x)), 6))
            except Exception:
                ys.append(None)
        return ys
    except Exception as e:
        return {"error": str(e)}
'''


ARCSIG_FFT_SPECTRUM_IMPL = '''def arcsig_fft_spectrum(arcsig: str) -> list:
    """Decode an ARCSIG signal and return its one-sided DFT spectrum.

    Format: ARCSIG:v1;SR:<hz>;LEN:<n>;ENC:f32le_b64;<base64 of float32 LE>
    Returns [{"freq_hz": k*sr/n (6 dp), "magnitude": abs(dft[k])/n (4 dp)}
    for k = 0..n//2], or {"error": ...} on malformed input.
    """
    import base64, struct, math, cmath
    try:
        parts = arcsig.strip().split(";")
        fields = {}
        for part in parts[:-1]:
            for sep in (":", "="):
                if sep in part:
                    key, val = part.split(sep, 1)
                    fields[key] = val
                    break
        sr = int(fields["SR"])
        n = int(fields["LEN"])
        raw = base64.b64decode(parts[-1])
        samples = list(struct.unpack("<%df" % n, raw[: n * 4]))
        spectrum = []
        for k in range(n // 2 + 1):
            c = sum(
                samples[j] * cmath.exp(-2j * math.pi * k * j / n)
                for j in range(n)
            )
            freq_hz = round(k * sr / n, 6)
            mag = round(abs(c) / n, 4)
            spectrum.append({"freq_hz": freq_hz, "magnitude": mag})
        return spectrum
    except Exception as e:
        return {"error": str(e)}
'''


ARCSIG_BANDPASS_FILTER_IMPL = '''def arcsig_bandpass_filter(arcsig: str, bandpass: str) -> str:
    """Band-pass filter an ARCSIG signal in the frequency domain.

    Decodes the signal, zeroes every DFT bin whose frequency magnitude lies
    strictly outside [low_hz, high_hz] (mirror bins included), inverse
    transforms, and re-encodes with the same SR/LEN. Filter spec format:
    BANDPASS:<low_hz>,<high_hz>. Returns the filtered ARCSIG string, or
    {"error": ...} on malformed input.
    """
    import base64, struct, math, cmath
    try:
        parts = arcsig.strip().split(";")
        fields = {}
        for part in parts[:-1]:
            for sep in (":", "="):
                if sep in part:
                    key, val = part.split(sep, 1)
                    fields[key] = val
                    break
        sr = int(fields["SR"])
        n = int(fields["LEN"])
        raw = base64.b64decode(parts[-1])
        samples = list(struct.unpack("<%df" % n, raw[: n * 4]))
        band = bandpass.split(":", 1)[1] if ":" in bandpass else bandpass
        low_s, high_s = band.split(",", 1)
        low, high = float(low_s), float(high_s)
        spec = [
            sum(samples[j] * cmath.exp(-2j * math.pi * k * j / n) for j in range(n))
            for k in range(n)
        ]
        for k in range(n):
            freq = k * sr / n if k <= n // 2 else (k - n) * sr / n
            if not (low <= abs(freq) <= high):
                spec[k] = 0j
        filtered = [
            (sum(spec[k] * cmath.exp(2j * math.pi * k * j / n) for k in range(n)) / n).real
            for j in range(n)
        ]
        payload = base64.b64encode(struct.pack("<%df" % n, *filtered)).decode("ascii")
        return "ARCSIG:v1;SR:%d;LEN:%d;ENC=f32le_b64;%s" % (sr, n, payload)
    except Exception as e:
        return {"error": str(e)}
'''


REFERENCE_IMPLS = {
    "arcfit_curve_fit": {
        "session_id": "numerical_s1",
        "task_id": "gap_1",
        "name": "arcfit_curve_fit",
        "implementation": ARCFIT_CURVE_FIT_IMPL,
    },
    "arcfit_model_evaluate": {
        "session_id": "numerical_s1",
        "task_id": "gap_2",
        "name": "arcfit_model_evaluate",
        "implementation": ARCFIT_MODEL_EVALUATE_IMPL,
    },
    "arcsig_fft_spectrum": {
        "session_id": "numerical_s2",
        "task_id": "gap_1",
        "name": "arcsig_fft_spectrum",
        "implementation": ARCSIG_FFT_SPECTRUM_IMPL,
    },
    "arcsig_bandpass_filter": {
        "session_id": "numerical_s2",
        "task_id": "gap_2",
        "name": "arcsig_bandpass_filter",
        "implementation": ARCSIG_BANDPASS_FILTER_IMPL,
    },
}
