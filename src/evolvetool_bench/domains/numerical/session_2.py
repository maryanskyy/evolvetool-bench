"""Domain C, Session 2: Custom Signal Processing.

Key design principle: tasks use a PROPRIETARY signal encoding format (ARCSIG)
that no LLM can solve from training data. The agent MUST create and execute tools.

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (compute_stats, solve_linear, interpolate_1d)
  Gap 1:     Decode ARCSIG format and compute frequency spectrum (FFT magnitudes)
  Gap 2:     Filter ARCSIG signal by retaining only a specified frequency band
  Variant 1: Decode a different ARCSIG signal (different waveform composition)
  Variant 2: Apply band-pass filter with different cutoff frequencies
  Compose 1: Decode signal → filter → compute stats on filtered time-domain samples
  Regress 1: Re-decode an ARCSIG signal (same format, different samples)
  Adversarial 1: ARCSIG with DC offset and a single-sample signal
  Adversarial 2: Band filter with very narrow band (may zero out all components)
"""

import base64
import math
import struct
import json
from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── Proprietary format: ARCSIG ────────────────────────────────────────────────
#
# ARCSIG encodes a 1-D time-domain signal as a text header + base64 payload.
#
# Format (single line):
#   ARCSIG:v1;SR:<sample_rate_hz>;LEN:<n_samples>;ENC:f32le_b64;<base64_payload>
#
# Encoding rules:
#   - sample_rate_hz: integer, samples per second
#   - n_samples: integer, number of float32 samples
#   - ENC field is always "f32le_b64" meaning IEEE 754 single-precision
#     little-endian floats, then base64-encoded.
#   - The base64 payload encodes exactly n_samples * 4 bytes.
#
# Gap 1 (spectrum): decode → numpy FFT → return list of
#   {"freq_hz": <float>, "magnitude": <float>}
#   for bins 0 .. n_samples//2  (one-sided spectrum), magnitudes rounded to 4 dp.
#   Magnitude = abs(fft[k]) / n_samples  (normalized)
#
# Gap 2 (filter): decode → zero out FFT bins outside [low_hz, high_hz] → IFFT →
#   re-encode into a new ARCSIG string (same SR and LEN).
#   Filter spec format: BANDPASS:<low_hz>,<high_hz>
#
# Note: agents must discover and implement all of this from the task description
# and the format spec above — the exact formula is not in training data.

def _encode_arcsig(samples: list[float], sample_rate: int) -> str:
    """Encode a list of float samples into ARCSIG format."""
    n = len(samples)
    payload_bytes = struct.pack(f"<{n}f", *samples)
    b64 = base64.b64encode(payload_bytes).decode("ascii")
    return f"ARCSIG:v1;SR:{sample_rate};LEN:{n};ENC:f32le_b64;{b64}"


def _make_signal(
    freqs_amps: list[tuple[float, float]],
    sample_rate: int,
    n_samples: int,
    dc_offset: float = 0.0,
) -> list[float]:
    """Synthesize a signal as sum of sinusoids."""
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        y = dc_offset + sum(amp * math.sin(2 * math.pi * f * t) for f, amp in freqs_amps)
        # quantise to float32 precision to match encode/decode round-trip
        samples.append(struct.unpack("<f", struct.pack("<f", y))[0])
    return samples


# ── Generate signals ──────────────────────────────────────────────────────────
_SR = 100          # 100 Hz sample rate
_N = 128           # 128 samples (short for determinism)

# Signal 1: 5 Hz (amp=1.0) + 20 Hz (amp=0.5)
_FREQS1 = [(5.0, 1.0), (20.0, 0.5)]
_SAMPLES1 = _make_signal(_FREQS1, _SR, _N)
ARCSIG_1 = _encode_arcsig(_SAMPLES1, _SR)

# Signal 2: 10 Hz (amp=2.0) + 30 Hz (amp=1.0) + 40 Hz (amp=0.25)
_FREQS2 = [(10.0, 2.0), (30.0, 1.0), (40.0, 0.25)]
_SAMPLES2 = _make_signal(_FREQS2, _SR, _N)
ARCSIG_2 = _encode_arcsig(_SAMPLES2, _SR)

# Signal 3 (variant / regress): 2 Hz (amp=3.0) + 15 Hz (amp=0.8)
_FREQS3 = [(2.0, 3.0), (15.0, 0.8)]
_SAMPLES3 = _make_signal(_FREQS3, _SR, _N)
ARCSIG_3 = _encode_arcsig(_SAMPLES3, _SR)

# Signal adversarial: DC offset + single frequency
_SAMPLES_ADV = _make_signal([(5.0, 0.01)], _SR, _N, dc_offset=100.0)
ARCSIG_ADV = _encode_arcsig(_SAMPLES_ADV, _SR)

# Single-sample edge case
ARCSIG_SINGLE = _encode_arcsig([1.0], _SR)


def _fft_spectrum(samples: list[float], sr: int) -> list[dict]:
    """Reference FFT for building expected outputs."""
    import cmath
    n = len(samples)
    # DFT brute force for small N (avoids numpy dependency here)
    result = []
    for k in range(n // 2 + 1):
        c = sum(
            samples[j] * cmath.exp(-2j * math.pi * k * j / n)
            for j in range(n)
        )
        freq_hz = round(k * sr / n, 6)
        mag = round(abs(c) / n, 4)
        result.append({"freq_hz": freq_hz, "magnitude": mag})
    return result


# Pre-compute expected spectrum for signal 1
_SPECTRUM1 = _fft_spectrum(_SAMPLES1, _SR)


# ── Expected filtered samples (band-pass 1–10 Hz on signal 1) ────────────────
# We can't easily compute this without numpy here; we record the ARCSIG string
# produced by a reference implementation. Instead store the filter spec and
# let the evaluator verify by re-running the agent's tool.
def _bandpass_verify(low: float, high: float) -> str:
    """Build a verify expression that decodes a returned ARCSIG string and
    checks the dominant DFT frequency lies in [low, high] Hz with out-of-band
    magnitude below 1e-3 of the in-band peak. Accepts both ENC: and ENC=
    header separators. A single eval-able expression, as the harness requires."""
    return (
        "(lambda res: isinstance(res, str) and res.startswith('ARCSIG') and "
        "(lambda parts: (lambda sr, xs: (lambda n: (lambda mags: (lambda inb, outb: "
        f"max(inb) > 0 and ({low} <= ([k for k, m in enumerate(mags) if m == max(inb)][0]) * sr / n <= {high}) "
        "and (max(outb) if outb else 0.0) < 1e-3 * max(inb)"
        f")([m for k, m in enumerate(mags) if k > 0 and {low} <= k * sr / n <= {high}], "
        f"[m for k, m in enumerate(mags) if k > 0 and not ({low} <= k * sr / n <= {high})])"
        ")([abs(sum(xs[j] * __import__('cmath').exp(-2j * __import__('cmath').pi * j * k / n) for j in range(n))) for k in range(n // 2 + 1)])"
        ")(len(xs)))("
        "int([p for p in parts if p.replace('=', ':').startswith('SR')][0].replace('=', ':').split(':')[-1]), "
        "__import__('struct').unpack('<%df' % (len(__import__('base64').b64decode(parts[-1])) // 4), __import__('base64').b64decode(parts[-1]))"
        "))(res.split(';')))(result)"
    )


BANDPASS_SPEC_1 = "BANDPASS:1,10"    # keep 5 Hz, reject 20 Hz
BANDPASS_SPEC_2 = "BANDPASS:15,45"   # keep 20 Hz from signal 1, reject 5 Hz
BANDPASS_SPEC_3 = "BANDPASS:1,12"    # keep 10 Hz from signal 2
BANDPASS_SPEC_NARROW = "BANDPASS:50,55"  # nothing in signal 1 → near-zero output


TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Compute statistics for these signal amplitude samples:\n"
            "[0.84, -0.54, 0.91, -0.99, 0.14, 0.66, -0.76, 0.96, -0.28, -0.47]\n\n"
            "Return mean, median, and population standard deviation."
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description=(
            "A signal is sampled at 50 Hz. At t=0.1 s the amplitude is 3.7, "
            "at t=0.3 s it is 8.2. Use linear interpolation to estimate the "
            "amplitude at t=0.2 s."
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "Solve for [A, B] in the linear system:\n"
            "  3A + 2B = 14\n"
            "  A  - 4B = -2\n\n"
            "Return A and B as floats."
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks ────────────────────────────────────────────────
    Task(
        id="gap_1",
        description=(
            "Decode the following ARCSIG signal and compute its one-sided frequency spectrum.\n\n"
            "ARCSIG format:\n"
            "  ARCSIG:v1;SR:<sample_rate_hz>;LEN:<n_samples>;ENC:f32le_b64;<base64>\n"
            "Decoding: base64-decode the payload, then unpack as little-endian IEEE 754 "
            "float32 values (4 bytes each).\n\n"
            "Spectrum computation:\n"
            "  1. Apply numpy FFT to the decoded samples.\n"
            "  2. For bins k = 0 … N//2 (inclusive), compute:\n"
            "       freq_hz = k * sample_rate / N\n"
            "       magnitude = abs(fft[k]) / N   (normalized)\n"
            "  3. Round freq_hz and magnitude to 4 decimal places.\n\n"
            f"Signal: {ARCSIG_1}\n\n"
            "Return a JSON list of objects: [{\"freq_hz\": ..., \"magnitude\": ...}, ...]"
        ),
        task_type=TaskType.GAP,
        capability_id="arcsig_fft_spectrum",
        expected=_SPECTRUM1,
        hidden_tests=[
            # v1
            {"input": {"arcsig": ARCSIG_2}, "expected": _fft_spectrum(_SAMPLES2, _SR)},
            {"input": {"arcsig": _encode_arcsig([1.0, -1.0, 1.0, -1.0], _SR)},
             "expected": _fft_spectrum([1.0, -1.0, 1.0, -1.0], _SR)},
            # v3 expansion
            {"input": {"arcsig": ARCSIG_1},
             "verify": "isinstance(result, list) and all('freq_hz' in d and 'magnitude' in d for d in result)"},
            {"input": {"arcsig": _encode_arcsig([1.0] + [0.0] * 7, _SR)},
             "verify": "isinstance(result, list) and len(result) > 0"},
            {"input": {"arcsig": _encode_arcsig([0.5] * 16, _SR)},
             "verify": "isinstance(result, list) and result[0]['magnitude'] > result[1]['magnitude']"},  # DC dominant
        ],
        adversarial_tests=[
            # v1
            {"input": {"arcsig": ARCSIG_SINGLE}},
            {"input": {"arcsig": ARCSIG_ADV}},
            {"input": {"arcsig": _encode_arcsig([0.0] * 8, _SR)}},
            # v3 expansion
            {"input": {"arcsig": ""}},
            {"input": {"arcsig": "ARCSIG:malformed_no_payload"}},
            {"input": {"arcsig": "SR=44100;LEN=4;ENC=f32le_b64;DATA=!!!not-base64!!!"}},
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Apply a band-pass filter to an ARCSIG signal.\n\n"
            "Filter spec format: BANDPASS:<low_hz>,<high_hz>\n\n"
            "Algorithm:\n"
            "  1. Decode the ARCSIG to get samples and sample_rate.\n"
            "  2. Compute numpy FFT of the samples.\n"
            "  3. Zero out all FFT bins where the corresponding frequency is "
            "     strictly outside [low_hz, high_hz]. Both positive and negative "
            "     frequency bins must be handled (mirror symmetry for real signals).\n"
            "  4. Compute IFFT, take real part.\n"
            "  5. Re-encode the filtered samples as a new ARCSIG string "
            "     (same SR and LEN, same ENC=f32le_b64).\n\n"
            f"Signal: {ARCSIG_1}\n"
            f"Filter: {BANDPASS_SPEC_1}\n\n"
            "Return the filtered ARCSIG string."
        ),
        task_type=TaskType.GAP,
        capability_id="arcsig_bandpass_filter",
        # Verifier checks that decoded filtered signal has dominant freq in [1,10] Hz
        hidden_tests=[
            # v1 — verify decodes the returned ARCSIG and checks the dominant
            # frequency lies in the passband with out-of-band energy suppressed
            # (these two tests originally had neither "expected" nor "verify",
            # making them unpassable by construction; fixed in v3.1)
            {"input": {"arcsig": ARCSIG_2, "bandpass": BANDPASS_SPEC_3},
             "verify": _bandpass_verify(1, 12)},
            {"input": {"arcsig": ARCSIG_1, "bandpass": BANDPASS_SPEC_2},
             "verify": _bandpass_verify(15, 45)},
            # v3 expansion
            {"input": {"arcsig": ARCSIG_1, "bandpass": "BANDPASS:0,1000"},
             "verify": "isinstance(result, str) and 'ARCSIG' in result"},
            {"input": {"arcsig": ARCSIG_2, "bandpass": "BANDPASS:10,30"},
             "verify": "isinstance(result, str) and 'ENC=f32le_b64' in result"},
            {"input": {"arcsig": _encode_arcsig([1.0] * 16, _SR), "bandpass": "BANDPASS:0,100"},
             "verify": "isinstance(result, str) and len(result) > 20"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"arcsig": ARCSIG_1, "bandpass": BANDPASS_SPEC_NARROW}},
            {"input": {"arcsig": ARCSIG_SINGLE, "bandpass": BANDPASS_SPEC_1}},
            {"input": {"arcsig": ARCSIG_ADV, "bandpass": "BANDPASS:0,0"}},
            # v3 expansion
            {"input": {"arcsig": ARCSIG_1, "bandpass": "BANDPASS:-1,1"}},   # negative low
            {"input": {"arcsig": ARCSIG_1, "bandpass": "BANDPASS:100,50"}}, # inverted range
            {"input": {"arcsig": "", "bandpass": "BANDPASS:1,10"}},          # empty signal
        ],
    ),

    # ── Variant tasks ─────────────────────────────────────────────
    Task(
        id="variant_1",
        description=(
            "Decode this ARCSIG signal and compute its frequency spectrum. "
            "Same format as before.\n\n"
            f"Signal: {ARCSIG_2}\n\n"
            "Return a JSON list of {\"freq_hz\": ..., \"magnitude\": ...} objects."
        ),
        task_type=TaskType.VARIANT,
        capability_id="arcsig_fft_spectrum",
        reuses_task="gap_1",
        expected=_fft_spectrum(_SAMPLES2, _SR),
    ),
    Task(
        id="variant_2",
        description=(
            "Apply a band-pass filter to this ARCSIG signal. Same format as before.\n\n"
            f"Signal: {ARCSIG_2}\n"
            f"Filter: {BANDPASS_SPEC_3}\n\n"
            "Return the filtered ARCSIG string."
        ),
        task_type=TaskType.VARIANT,
        capability_id="arcsig_bandpass_filter",
        reuses_task="gap_2",
    ),

    # ── Compose task ──────────────────────────────────────────────
    Task(
        id="compose_1",
        description=(
            "Decode the ARCSIG signal, apply the band-pass filter to isolate the "
            "low-frequency component, then compute statistics (mean, median, std) "
            "of the filtered time-domain samples.\n\n"
            f"Signal: {ARCSIG_2}\n"
            f"Filter: {BANDPASS_SPEC_3}\n\n"
            "Return a JSON object with keys 'filtered_arcsig' (the filtered ARCSIG string) "
            "and 'stats' (mean, median, std of the filtered samples)."
        ),
        task_type=TaskType.COMPOSE,
        capability_id="arcsig_filter_plus_stats",
        composes_tasks=["gap_1", "gap_2", "seed_1"],
    ),

    # ── Regress task ──────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            "Decode this ARCSIG signal and compute its frequency spectrum "
            "(same format as before).\n\n"
            f"Signal: {ARCSIG_3}\n\n"
            "Return a JSON list of {\"freq_hz\": ..., \"magnitude\": ...} objects."
        ),
        task_type=TaskType.REGRESS,
        capability_id="arcsig_fft_spectrum",
        reuses_task="gap_1",
        expected=_fft_spectrum(_SAMPLES3, _SR),
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Decode this ARCSIG signal and compute its frequency spectrum. "
            "WARNING: the signal has a very large DC offset (constant value ≈ 100). "
            "Your tool must not overflow, crash, or produce NaN magnitudes.\n\n"
            f"Signal: {ARCSIG_ADV}\n\n"
            "Return a JSON list of {\"freq_hz\": ..., \"magnitude\": ...} objects. "
            "The DC bin (freq_hz=0) magnitude should be approximately 100."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="arcsig_fft_spectrum",
        breaks_task="gap_1",
        expected=_fft_spectrum(_SAMPLES_ADV, _SR),
    ),
    Task(
        id="adversarial_2",
        description=(
            "Apply a very narrow band-pass filter to an ARCSIG signal. "
            "The pass band contains NO significant frequency components, "
            "so the filtered output should be near-zero everywhere. "
            "Your tool must return a valid ARCSIG string and not crash.\n\n"
            f"Signal: {ARCSIG_1}\n"
            f"Filter: {BANDPASS_SPEC_NARROW}\n\n"
            "Return the filtered ARCSIG string. All sample magnitudes should be < 0.01."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="arcsig_bandpass_filter",
        breaks_task="gap_2",
    ),
]


def create_session() -> Session:
    return Session(
        id="numerical_s2",
        name="Custom Signal Processing (ARCSIG format)",
        domain="numerical",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description=(
            "Tests tool creation for a proprietary signal encoding format (ARCSIG). "
            "Gap tasks require binary decoding, FFT-based spectral analysis, and "
            "frequency-domain filtering. Cannot be solved from training data."
        ),
    )
