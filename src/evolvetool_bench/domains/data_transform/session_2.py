"""Domain A, Session 2: Custom Schema Language (VDL — Validation Definition Language).

Key design principle: tasks use CUSTOM ENCODINGS that the LLM cannot
solve from training data. The agent MUST create and execute tools.

VDL (Validation Definition Language) is a proprietary schema format:
  - Each line defines a field: `field_name : type_code [ flags ]`
  - Type codes: S=string, I=integer, F=float, B=boolean, E(val1|val2)=enum
  - Flags: R=required, U=unique, N=nullable, V(min..max)=range validator
  - Nested objects use indented blocks with `> object_name :`
  - Arrays use `* field_name : type_code`
  - Comments start with `#`
  - Schema header: `@schema schema_name @version N`

Session structure (11 tasks):
  Seed 1-3:  Use provided tools (read_csv, write_json, compute_hash)
  Gap 1:     Parse VDL schema into structured representation
  Gap 2:     Validate data records against a parsed VDL schema
  Variant 1: Parse a different VDL schema — should REUSE gap_1
  Variant 2: Validate different data against different schema — should REUSE gap_2
  Compose 1: Parse schema then validate data (chain gap_1 + gap_2)
  Regress 1: Re-parse the original schema
  Adversarial 1: VDL with deeply nested objects and edge-case types
  Adversarial 2: Data with type coercion edge cases against strict schema
"""

from ...types import Task, TaskType, Session
from .seed_tools import SEED_TOOLS


# ── VDL Format Definition ────────────────────────────────────────────
# This is a completely custom schema language — NOT JSON Schema, NOT protobuf,
# NOT any standard format. The LLM must write a parser from scratch.

def _parse_vdl(vdl_text: str) -> dict:
    """Reference parser for VDL schemas. Returns structured representation."""
    lines = vdl_text.strip().split('\n')
    schema = {"name": "", "version": 0, "fields": []}
    field_stack = [schema["fields"]]  # stack for nested objects
    indent_stack = [0]

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Header
        if stripped.startswith('@schema'):
            parts = stripped.split()
            schema["name"] = parts[1] if len(parts) > 1 else ""
            for i, p in enumerate(parts):
                if p == '@version' and i + 1 < len(parts):
                    schema["version"] = int(parts[i + 1])
            continue

        indent = len(line) - len(line.lstrip())

        # Pop stack if we've dedented
        while len(indent_stack) > 1 and indent <= indent_stack[-1]:
            indent_stack.pop()
            field_stack.pop()

        field_def = _parse_field_line(stripped)
        if field_def:
            field_stack[-1].append(field_def)
            # If it's a nested object, push its children list
            if field_def["type"] == "object":
                field_def["children"] = []
                field_stack.append(field_def["children"])
                indent_stack.append(indent)

    return schema


def _parse_field_line(line: str) -> dict | None:
    """Parse a single VDL field definition line."""
    # Nested object: `> object_name :`
    if line.startswith('>'):
        name = line[1:].strip().rstrip(':').strip()
        return {"name": name, "type": "object", "flags": [], "children": []}

    # Array field: `* field_name : type_code`
    is_array = line.startswith('*')
    if is_array:
        line = line[1:].strip()

    # Split name : type [flags]
    if ':' not in line:
        return None

    name_part, rest = line.split(':', 1)
    name = name_part.strip()
    rest = rest.strip()

    # Extract flags in brackets
    flags = []
    while '[' in rest:
        start = rest.index('[')
        end = rest.index(']', start)
        flag_content = rest[start + 1:end]
        flags.append(flag_content)
        rest = rest[:start] + rest[end + 1:]
    rest = rest.strip()

    # Parse type code
    type_info = _parse_type_code(rest)

    result = {"name": name, "is_array": is_array, "flags": flags}
    result.update(type_info)
    return result


def _parse_type_code(code: str) -> dict:
    """Parse a VDL type code."""
    code = code.strip()
    if code == 'S':
        return {"type": "string"}
    elif code == 'I':
        return {"type": "integer"}
    elif code == 'F':
        return {"type": "float"}
    elif code == 'B':
        return {"type": "boolean"}
    elif code.startswith('E(') and code.endswith(')'):
        values = code[2:-1].split('|')
        return {"type": "enum", "values": [v.strip() for v in values]}
    else:
        return {"type": "unknown", "raw": code}


def _validate_against_vdl(schema_fields: list[dict], record: dict) -> list[str]:
    """Validate a single record against parsed VDL fields. Returns list of errors."""
    errors = []
    for field_def in schema_fields:
        name = field_def["name"]
        flags = field_def.get("flags", [])
        is_required = any(f == 'R' for f in flags)
        is_nullable = any(f == 'N' for f in flags)

        if name not in record:
            if is_required:
                errors.append(f"missing required field: {name}")
            continue

        value = record[name]
        if value is None:
            if not is_nullable:
                errors.append(f"field '{name}' is not nullable")
            continue

        # Type check
        expected_type = field_def.get("type", "unknown")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"field '{name}' expected string, got {type(value).__name__}")
        elif expected_type == "integer" and not isinstance(value, int):
            errors.append(f"field '{name}' expected integer, got {type(value).__name__}")
        elif expected_type == "float" and not isinstance(value, (int, float)):
            errors.append(f"field '{name}' expected float, got {type(value).__name__}")
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"field '{name}' expected boolean, got {type(value).__name__}")
        elif expected_type == "enum":
            if value not in field_def.get("values", []):
                errors.append(f"field '{name}' value '{value}' not in enum {field_def['values']}")

        # Range validator
        for flag in flags:
            if flag.startswith('V(') and flag.endswith(')'):
                range_str = flag[2:-1]
                if '..' in range_str:
                    lo, hi = range_str.split('..')
                    try:
                        lo_val = float(lo) if lo else float('-inf')
                        hi_val = float(hi) if hi else float('inf')
                        if isinstance(value, (int, float)) and not (lo_val <= value <= hi_val):
                            errors.append(f"field '{name}' value {value} out of range [{lo}..{hi}]")
                    except (ValueError, TypeError):
                        pass

    return errors


# ── Test data: VDL schemas ───────────────────────────────────────────

USER_VDL = """@schema UserProfile @version 1
# User profile schema
username : S [R] [U]
email : S [R]
age : I [R] [V(0..150)]
score : F [N]
role : E(admin|editor|viewer) [R]
"""

PRODUCT_VDL = """@schema ProductCatalog @version 2
# Product catalog entry
sku : S [R] [U]
name : S [R]
price : F [R] [V(0..99999)]
in_stock : B
category : E(electronics|clothing|food|other) [R]
weight_kg : F [N] [V(0..1000)]
"""

NESTED_VDL = """@schema OrderRecord @version 1
order_id : S [R] [U]
status : E(pending|shipped|delivered|cancelled) [R]
> customer :
    name : S [R]
    email : S [R]
    > address :
        street : S [R]
        city : S [R]
        zip : S
* items : S
total : F [R] [V(0..)]
"""

# Expected parse results
USER_VDL_PARSED = {
    "name": "UserProfile",
    "version": 1,
    "fields": [
        {"name": "username", "type": "string", "is_array": False, "flags": ["R", "U"]},
        {"name": "email", "type": "string", "is_array": False, "flags": ["R"]},
        {"name": "age", "type": "integer", "is_array": False, "flags": ["R", "V(0..150)"]},
        {"name": "score", "type": "float", "is_array": False, "flags": ["N"]},
        {"name": "role", "type": "enum", "values": ["admin", "editor", "viewer"],
         "is_array": False, "flags": ["R"]},
    ],
}

PRODUCT_VDL_PARSED = {
    "name": "ProductCatalog",
    "version": 2,
    "fields": [
        {"name": "sku", "type": "string", "is_array": False, "flags": ["R", "U"]},
        {"name": "name", "type": "string", "is_array": False, "flags": ["R"]},
        {"name": "price", "type": "float", "is_array": False, "flags": ["R", "V(0..99999)"]},
        {"name": "in_stock", "type": "boolean", "is_array": False, "flags": []},
        {"name": "category", "type": "enum", "values": ["electronics", "clothing", "food", "other"],
         "is_array": False, "flags": ["R"]},
        {"name": "weight_kg", "type": "float", "is_array": False, "flags": ["N", "V(0..1000)"]},
    ],
}

# Validation test data
VALID_USERS = [
    {"username": "alice", "email": "alice@test.com", "age": 30, "score": 95.5, "role": "admin"},
    {"username": "bob", "email": "bob@test.com", "age": 25, "score": None, "role": "viewer"},
]

INVALID_USERS = [
    {"username": "charlie", "age": 28, "role": "editor"},  # missing email
    {"username": "diana", "email": "d@t.com", "age": 200, "role": "admin"},  # age out of range
    {"username": "eve", "email": "e@t.com", "age": 22, "role": "superuser"},  # invalid enum
]

VALID_PRODUCTS = [
    {"sku": "EL-001", "name": "Widget", "price": 9.99, "in_stock": True, "category": "electronics"},
]

INVALID_PRODUCTS = [
    {"sku": "CL-001", "name": "Shirt", "price": -5.0, "category": "clothing"},  # negative price
    {"name": "Hat", "price": 15.0, "category": "clothing"},  # missing sku
]

# Validation expected results
INVALID_USERS_RESULTS = [
    {"valid": False, "errors": ["missing required field: email"]},
    {"valid": False, "errors": ["field 'age' value 200 out of range [0..150]"]},
    {"valid": False, "errors": ["field 'role' value 'superuser' not in enum ['admin', 'editor', 'viewer']"]},
]

VALID_USERS_RESULTS = [
    {"valid": True, "errors": []},
    {"valid": True, "errors": []},
]

VALID_PRODUCTS_RESULTS = [
    {"valid": True, "errors": []},
]

INVALID_PRODUCTS_RESULTS = [
    {"valid": False, "errors": ["field 'price' value -5.0 out of range [0..99999]"]},
    {"valid": False, "errors": ["missing required field: sku"]},
]


# ── Tasks ────────────────────────────────────────────────────────────

TASKS = [
    # ── Seed tasks ───────────────────────────────────────────────
    Task(
        id="seed_1",
        description=(
            "Read this CSV and convert it to JSON:\n"
            "field,type,required\nusername,string,true\nemail,string,true\nage,integer,true"
        ),
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_2",
        description='Compute the SHA-256 hash of "vdl-schema-v1".',
        task_type=TaskType.SEED,
    ),
    Task(
        id="seed_3",
        description=(
            "Read this CSV, then output the data as JSON:\n"
            "schema,version,fields\nUserProfile,1,5\nProductCatalog,2,6"
        ),
        task_type=TaskType.SEED,
    ),

    # ── Gap tasks (require creating new tools) ───────────────────
    Task(
        id="gap_1",
        description=(
            "Parse this VDL (Validation Definition Language) schema into a structured representation.\n\n"
            "VDL format rules:\n"
            "- Header: `@schema name @version N`\n"
            "- Each field: `field_name : type_code [flags]`\n"
            "- Type codes: S=string, I=integer, F=float, B=boolean, E(val1|val2)=enum\n"
            "- Flags in brackets: R=required, U=unique, N=nullable, V(min..max)=range\n"
            "- Nested objects: `> object_name :` followed by indented fields\n"
            "- Array fields: `* field_name : type_code`\n"
            "- Comments start with `#`\n\n"
            "Schema:\n"
            f"{USER_VDL}\n\n"
            "Return a dict with keys: name (str), version (int), fields (list of field dicts).\n"
            "Each field dict should have: name, type, is_array, flags.\n"
            "For enum types, also include 'values' list."
        ),
        task_type=TaskType.GAP,
        capability_id="vdl_schema_parse",
        expected=USER_VDL_PARSED,
        hidden_tests=[
            # v1
            {"input": {"vdl_text": "@schema Test @version 1\nfoo : S [R]\nbar : I [N]"},
             "expected": {"name": "Test", "version": 1,
                          "fields": [{"name": "foo", "type": "string", "is_array": False, "flags": ["R"]},
                                     {"name": "bar", "type": "integer", "is_array": False, "flags": ["N"]}]}},
            {"input": {"vdl_text": "@schema Enum @version 1\ncolor : E(red|green|blue) [R]"},
             "expected": {"name": "Enum", "version": 1,
                          "fields": [{"name": "color", "type": "enum", "values": ["red", "green", "blue"],
                                       "is_array": False, "flags": ["R"]}]}},
            # v3 expansion
            {"input": {"vdl_text": "@schema Bool @version 2\nactive : B [R]\ndeleted : B [N]"},
             "expected": {"name": "Bool", "version": 2,
                          "fields": [{"name": "active", "type": "boolean", "is_array": False, "flags": ["R"]},
                                     {"name": "deleted", "type": "boolean", "is_array": False, "flags": ["N"]}]}},
            {"input": {"vdl_text": "@schema Arr @version 1\ntags : S[] [R]"},
             "expected": {"name": "Arr", "version": 1,
                          "fields": [{"name": "tags", "type": "string", "is_array": True, "flags": ["R"]}]}},
            {"input": {"vdl_text": "@schema Float @version 3\nscore : F V(0..100) [R]"},
             "verify": "result['name'] == 'Float' and result['version'] == 3 and result['fields'][0]['type'] == 'float'"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"vdl_text": ""}},
            {"input": {"vdl_text": "# just a comment\n"}},
            {"input": {"vdl_text": "@schema X @version 0"}},
            # v3 expansion
            {"input": {"vdl_text": "@schema NoVer\nfoo : S"}},            # missing version
            {"input": {"vdl_text": "@schema X @version 1\nfoo : ?"}},     # unknown type code
            {"input": {"vdl_text": "@schema X @version abc\nfoo : S"}},   # non-numeric version
        ],
    ),
    Task(
        id="gap_2",
        description=(
            "Validate data records against a parsed VDL schema. The schema has been parsed into:\n\n"
            f"{USER_VDL_PARSED}\n\n"
            "Validate these records and return a list of validation results.\n"
            "Each result: {{'valid': bool, 'errors': list[str]}}\n\n"
            "Validation rules:\n"
            "- Check required fields (flag 'R') are present\n"
            "- Check types match (string/integer/float/boolean/enum)\n"
            "- Check range constraints V(min..max)\n"
            "- Nullable fields (flag 'N') can be None\n"
            "- Non-nullable fields cannot be None\n\n"
            f"Records: {INVALID_USERS}"
        ),
        task_type=TaskType.GAP,
        capability_id="vdl_record_validate",
        expected=INVALID_USERS_RESULTS,
        hidden_tests=[
            # v1
            {"input": {"schema": USER_VDL_PARSED, "records": VALID_USERS},
             "expected": VALID_USERS_RESULTS},
            {"input": {"schema": USER_VDL_PARSED,
                       "records": [{"username": "x", "email": "x@x.com", "age": -1, "role": "admin"}]},
             "verify": "result[0]['valid'] is False and 'range' in result[0]['errors'][0]"},
            # v3 expansion
            {"input": {"schema": USER_VDL_PARSED,
                       "records": [{"username": "ok", "email": "ok@ok.com", "age": 30, "role": "admin"}]},
             "verify": "result[0]['valid'] is True"},
            {"input": {"schema": USER_VDL_PARSED,
                       "records": [{"username": "x", "email": "x@x.com", "role": "admin"}]},   # missing required age
             "verify": "result[0]['valid'] is False"},
            {"input": {"schema": USER_VDL_PARSED,
                       "records": [{"username": "x", "email": "x@x.com", "age": "thirty", "role": "admin"}]},   # wrong type
             "verify": "result[0]['valid'] is False"},
        ],
        adversarial_tests=[
            # v1
            {"input": {"schema": USER_VDL_PARSED, "records": []}},
            {"input": {"schema": {"name": "Empty", "version": 1, "fields": []}, "records": [{"x": 1}]}},
            {"input": {"schema": USER_VDL_PARSED, "records": [{}]}},
            # v3 expansion
            {"input": {"schema": USER_VDL_PARSED, "records": [None]}},                                # None record
            {"input": {"schema": None, "records": [{"x": 1}]}},                                       # None schema
            {"input": {"schema": USER_VDL_PARSED, "records": [{"username": None, "email": None, "age": None, "role": None}]}},
        ],
    ),

    # ── Variant tasks (should REUSE gap tools) ───────────────────
    Task(
        id="variant_1",
        description=(
            "Parse this VDL schema (same format as before):\n\n"
            f"{PRODUCT_VDL}\n\n"
            "Return the structured representation."
        ),
        task_type=TaskType.VARIANT,
        capability_id="vdl_schema_parse",
        reuses_task="gap_1",
        expected=PRODUCT_VDL_PARSED,
    ),
    Task(
        id="variant_2",
        description=(
            "Validate these product records against the product schema:\n\n"
            f"Schema: {PRODUCT_VDL_PARSED}\n\n"
            f"Records: {INVALID_PRODUCTS}\n\n"
            "Return validation results."
        ),
        task_type=TaskType.VARIANT,
        capability_id="vdl_record_validate",
        reuses_task="gap_2",
        expected=INVALID_PRODUCTS_RESULTS,
    ),

    # ── Compose task (chain gap_1 + gap_2) ─────────────────────
    Task(
        id="compose_1",
        description=(
            "Parse this VDL schema, then validate the given records against it.\n\n"
            f"Schema (VDL text):\n{USER_VDL}\n\n"
            f"Records: {VALID_USERS}\n\n"
            "First parse the VDL, then validate each record. Return validation results."
        ),
        task_type=TaskType.COMPOSE,
        capability_id="vdl_parse_plus_validate",
        composes_tasks=["gap_1", "gap_2"],
        expected=VALID_USERS_RESULTS,
    ),

    # ── Regress task ────────────────────────────────────────────
    Task(
        id="regress_1",
        description=(
            "Parse this VDL schema (same format as before):\n\n"
            "@schema Sensor @version 3\n"
            "sensor_id : S [R] [U]\n"
            "reading : F [R] [V(-50..200)]\n"
            "unit : E(celsius|fahrenheit|kelvin) [R]\n"
            "calibrated : B\n\n"
            "Return the structured representation."
        ),
        task_type=TaskType.REGRESS,
        capability_id="vdl_schema_parse",
        reuses_task="gap_1",
        expected={
            "name": "Sensor",
            "version": 3,
            "fields": [
                {"name": "sensor_id", "type": "string", "is_array": False, "flags": ["R", "U"]},
                {"name": "reading", "type": "float", "is_array": False, "flags": ["R", "V(-50..200)"]},
                {"name": "unit", "type": "enum", "values": ["celsius", "fahrenheit", "kelvin"],
                 "is_array": False, "flags": ["R"]},
                {"name": "calibrated", "type": "boolean", "is_array": False, "flags": []},
            ],
        },
    ),

    # ── Adversarial tasks ────────────────────────────────────────
    Task(
        id="adversarial_1",
        description=(
            "Parse this VDL schema with nested objects and array fields:\n\n"
            f"{NESTED_VDL}\n\n"
            "The parser must handle:\n"
            "- Nested `> object_name :` blocks (indentation-based)\n"
            "- Array fields with `*` prefix\n"
            "- Open-ended range V(0..)\n"
            "Return the structured representation."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="vdl_schema_parse",
        breaks_task="gap_1",
    ),
    Task(
        id="adversarial_2",
        description=(
            "Validate these edge-case records against the user schema:\n\n"
            f"Schema: {USER_VDL_PARSED}\n\n"
            "Records:\n"
            "1. {{'username': 123, 'email': 'a@b.com', 'age': 25, 'role': 'admin'}} - wrong type for username\n"
            "2. {{'username': 'test', 'email': 'x', 'age': 0, 'score': 'not_a_float', 'role': 'viewer'}} - wrong type for score\n"
            "3. {{'username': '', 'email': '', 'age': 150, 'role': 'admin'}} - boundary values\n\n"
            "Return validation results."
        ),
        task_type=TaskType.ADVERSARIAL,
        capability_id="vdl_record_validate",
        breaks_task="gap_2",
        expected=[
            {"valid": False, "errors": ["field 'username' expected string, got int"]},
            {"valid": False, "errors": ["field 'score' expected float, got str"]},
            {"valid": True, "errors": []},  # age=150 is within V(0..150)
        ],
    ),
]


def create_session() -> Session:
    return Session(
        id="data_transform_s2",
        name="Custom Schema Language (VDL)",
        domain="data_transform",
        tasks=TASKS,
        seed_tools=SEED_TOOLS,
        description="Tests tool creation for parsing and validating against a proprietary "
                    "schema language (VDL) that cannot be solved from LLM training data.",
    )
