"""Domain B, Session 1: API Authentication & Paginated Data Retrieval.

The mock API at localhost:18080 uses:
- HMAC-timestamp auth (not standard Bearer/OAuth)
- Cursor-based pagination with encrypted cursors
- Standard JSON responses

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (http_get, parse_json, format_table)
  Gap 1:     Authenticate with HMAC-timestamp scheme
  Gap 2:     Fetch ALL pages of paginated /api/users endpoint
  Variant 1: Authenticate with same scheme (different timestamp)
  Variant 2: Fetch ALL pages of /api/metrics endpoint
  Compose 1: Authenticate → fetch all users → compute average score
  Regress 1: Re-authenticate and fetch users (should reuse tools)
  Adversarial 1: Handle auth with clock skew
  Adversarial 2: Handle pagination with invalid/expired cursors
"""

from ...types import Task, TaskType, Session


SEED_TOOLS = [
    {
        "name": "http_get",
        "description": "Make an HTTP GET request and return the response body as string.",
        "implementation": '''
def http_get(url: str, headers: dict = None) -> str:
    """Make an HTTP GET request. Returns response body as string."""
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"
    except Exception as e:
        return f"Error: {e}"
''',
    },
    {
        "name": "parse_json",
        "description": "Parse a JSON string into a Python object.",
        "implementation": '''
def parse_json(json_string: str) -> dict:
    """Parse a JSON string into a Python dict/list."""
    import json
    return json.loads(json_string)
''',
    },
    {
        "name": "format_table",
        "description": "Format a list of dicts as a readable text table.",
        "implementation": '''
def format_table(data: list) -> str:
    """Format a list of dicts as a text table."""
    if not data:
        return "(empty)"
    keys = list(data[0].keys())
    widths = {k: max(len(str(k)), max(len(str(row.get(k, ""))) for row in data)) for k in keys}
    header = " | ".join(k.ljust(widths[k]) for k in keys)
    sep = "-+-".join("-" * widths[k] for k in keys)
    rows = ["\\n".join(str(row.get(k, "")).ljust(widths[k]) for k in keys) for row in data]
    return header + "\\n" + sep + "\\n" + "\\n".join(" | ".join(str(row.get(k, "")).ljust(widths[k]) for k in keys) for row in data)
''',
    },
]

BASE_URL = "http://127.0.0.1:18080"

TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=f"Check if the API server is healthy by making a GET request to {BASE_URL}/health and return the status.",
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description=f"Get the authentication info from {BASE_URL}/auth/info and tell me what authentication scheme this API uses.",
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=f"Make a GET request to {BASE_URL}/api/users (without auth) and tell me what error you get.",
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks ────────────────────────────────────────────────
    Task(
        id="gap_1",
        description=(
            f"Authenticate with the API at {BASE_URL}. "
            f"First, GET {BASE_URL}/auth/info to learn the auth scheme. "
            "Then create a tool that generates the correct auth header and "
            f"use it to fetch {BASE_URL}/api/users. "
            "Return the list of users from the first page."
        ),
        task_type=TaskType.GAP,
        capability_id="hmac_sha256_auth",
        hidden_tests=[
            # v1
            {"input": {"url": f"{BASE_URL}/api/users"},
             "verify": "isinstance(result, dict) and 'data' in str(result)"},
            # v3 expansion
            {"input": {"url": f"{BASE_URL}/api/users?cursor=cursor_5"},
             "verify": "isinstance(result, (dict, str)) and ('data' in str(result) or 'error' not in str(result).lower()[:20])"},
            {"input": {"url": f"{BASE_URL}/health"},
             "verify": "result is not None"},
            {"input": {"url": f"{BASE_URL}/auth/info"},
             "verify": "'algorithm' in str(result) or 'scheme' in str(result) or isinstance(result, dict)"},
            {"input": {"url": f"{BASE_URL}/api/users/3"},
             "verify": "isinstance(result, (dict, str))"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"url": f"{BASE_URL}/api/nonexistent"}},
            # v3 expansion
            {"input": {"url": "http://127.0.0.1:65535/api/users"}},     # unreachable port
            {"input": {"url": f"{BASE_URL}/api/users?cursor=BAD_CURSOR_!@#$"}},
            {"input": {"url": ""}},                                       # empty URL
            {"input": {"url": f"{BASE_URL}/api/users?cursor=" + "x" * 1000}},  # huge cursor
        ],
    ),
    Task(
        id="gap_2",
        description=(
            f"Fetch ALL users from {BASE_URL}/api/users. "
            "The API uses cursor-based pagination — each response has a 'pagination' "
            "field with 'next_cursor' and 'has_more'. You must follow cursors until "
            "has_more is false. Return the total number of users and their names."
        ),
        task_type=TaskType.GAP,
        capability_id="cursor_pagination",
        hidden_tests=[
            # v1
            {"input": {}, "verify": "'10' in str(result) or 'Jack' in str(result)"},
            # v3 expansion
            {"input": {"page_size": 3},
             "verify": "isinstance(result, (dict, list, int, str)) and len(str(result)) > 0"},
            {"input": {"start_cursor": None},
             "verify": "result is not None"},
            {"input": {"max_pages": 10},
             "verify": "result is not None"},
            {"input": {},
             "verify": "any(name in str(result) for name in ['Alice','Bob','Charlie','Diana','Eve','Frank','Grace','Henry','Ivy','Jack'])"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"cursor": "invalid_cursor_value"}},
            # v3 expansion
            {"input": {"cursor": ""}},
            {"input": {"page_size": 0}},
            {"input": {"page_size": -1}},
            {"input": {"max_pages": 0}},
        ],
    ),

    # ── Variant tasks ────────────────────────────────────────────
    Task(
        id="variant_1",
        description=(
            f"Authenticate with {BASE_URL} and fetch the user with ID 5. "
            "Use the same auth scheme as before. Return the user's details."
        ),
        task_type=TaskType.VARIANT,
        capability_id="hmac_sha256_auth",
        reuses_task="gap_1",
    ),
    Task(
        id="variant_2",
        description=(
            f"Fetch ALL metrics from {BASE_URL}/api/metrics. "
            "Same pagination scheme as /api/users — follow cursors until done. "
            "Return the total count of metrics."
        ),
        task_type=TaskType.VARIANT,
        capability_id="cursor_pagination",
        reuses_task="gap_2",
    ),

    # ── Compose task ─────────────────────────────────────────────
    Task(
        id="compose_1",
        description=(
            f"Authenticate with {BASE_URL}, fetch ALL users (follow pagination), "
            "then compute the average score across all users. Return the average."
        ),
        task_type=TaskType.COMPOSE,
        capability_id="auth_plus_pagination",
        composes_tasks=["gap_1", "gap_2"],
    ),

    # ── Regress task ─────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            f"Authenticate with {BASE_URL} and fetch the first page of users. "
            "This is the same task as before — your auth and fetch tools should still work."
        ),
        task_type=TaskType.REGRESS,
        capability_id="hmac_sha256_auth",
        reuses_task="gap_1",
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            f"Authenticate with {BASE_URL} and fetch users. "
            "WARNING: Your auth timestamp must be within the valid window. "
            "If auth fails, retry with a fresh timestamp. Handle 401 errors gracefully."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="hmac_sha256_auth",
        breaks_task="gap_1",
    ),
    Task(
        id="adversarial_2",
        description=(
            f"Fetch events from {BASE_URL}/api/events filtered by type='error'. "
            "Also fetch events from source='svc-1'. "
            "Return both result sets. Handle any API errors gracefully."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="cursor_pagination",
        breaks_task="gap_2",
    ),
]


def create_session() -> Session:
    return Session(
        id="api_orchestration_s1",
        name="API Authentication & Paginated Retrieval",
        domain="api_orchestration",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description="Tests tool creation for HMAC-timestamp auth and cursor-based "
                    "pagination with encrypted cursors. Requires HTTP tool usage.",
    )
