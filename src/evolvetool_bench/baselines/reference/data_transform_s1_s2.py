"""Hand-crafted reference implementations for data_transform sessions 1 & 2 gap tasks.

These are calibration artifacts for the paper: they prove the held-out
conformance suites (hidden_tests) are passable by a correct implementation
(C = 1.00). They are NOT used by any baseline system at run time.

ABR / RLE implementations are taken from baselines/human_oracle.py (already
verified at C = 1.00). The VDL implementations are written fresh against the
session_2 hidden tests, since the old oracle `parse_vdl_schema` is stale
(wrong kwarg name and output shape).
"""

from __future__ import annotations


_DECODE_ABR = '''
def decode_abr(data: str) -> list:
    """Decode ABR format: base64 -> binary records with field_count, name/value pairs, 0xFF separators."""
    import base64, struct
    try:
        raw = base64.b64decode(data)
    except Exception:
        return []
    records = []
    i = 0
    while i < len(raw):
        if raw[i] == 0xFF:
            i += 1
            continue
        field_count = raw[i]; i += 1
        rec = {}
        truncated = False
        for _ in range(field_count):
            if i >= len(raw):
                truncated = True
                break
            name_len = raw[i]; i += 1
            if i + name_len > len(raw):
                truncated = True
                break
            name = raw[i:i+name_len].decode("utf-8", errors="replace"); i += name_len
            if i + 2 > len(raw):
                truncated = True
                break
            val_len = struct.unpack(">H", raw[i:i+2])[0]; i += 2
            val = raw[i:i+val_len].decode("utf-8", errors="replace"); i += min(val_len, len(raw) - i)
            rec[name] = val
        records.append(rec)
        if truncated:
            break
    return records
'''


_DECODE_RLE = '''
def decode_rle_matrix(rle_string: str) -> list:
    """Parse 'rows,cols;val:count,...' into a list of lists (rows x cols)."""
    try:
        header, data = rle_string.split(";", 1)
        rows, cols = map(int, header.split(","))
        flat = []
        if data.strip():
            for run in data.split(","):
                val, count = run.split(":")
                flat.extend([int(val)] * int(count))
        matrix = []
        for r in range(rows):
            matrix.append(flat[r*cols:(r+1)*cols])
        return matrix
    except Exception:
        return []
'''


_PARSE_VDL = '''
def parse_vdl_schema(vdl_text: str) -> dict:
    """Parse a VDL (Validation Definition Language) schema into a structured dict.

    Returns {"name": str, "version": int, "fields": [field, ...]} where each
    field is {"name", "type", "is_array", "flags"} plus "values" for enums.
    Types: S=string, I=integer, F=float, B=boolean, E(a|b|...)=enum.
    Arrays: `* name : T` prefix or `T[]` suffix. Flags appear in brackets.
    """
    schema = {"name": "", "version": 0, "fields": []}
    if not isinstance(vdl_text, str):
        return schema
    for raw_line in vdl_text.split("\\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@schema"):
            parts = line.split()
            if len(parts) > 1:
                schema["name"] = parts[1]
            for i, p in enumerate(parts):
                if p == "@version" and i + 1 < len(parts):
                    try:
                        schema["version"] = int(parts[i + 1])
                    except (ValueError, TypeError):
                        schema["version"] = 0
            continue
        # Nested object header `> name :` — record gracefully, no recursion needed
        if line.startswith(">"):
            name = line[1:].strip().rstrip(":").strip()
            schema["fields"].append({"name": name, "type": "object",
                                     "is_array": False, "flags": []})
            continue
        is_array = line.startswith("*")
        if is_array:
            line = line[1:].strip()
        if ":" not in line:
            continue
        name_part, rest = line.split(":", 1)
        name = name_part.strip()
        rest = rest.strip()
        # Extract bracketed groups: empty `[]` marks an array (e.g. `S[]`),
        # non-empty groups are flags (R, U, N, V(min..max)).
        flags = []
        while "[" in rest and "]" in rest[rest.index("["):]:
            start = rest.index("[")
            end = rest.index("]", start)
            content = rest[start + 1:end].strip()
            if content:
                flags.append(content)
            else:
                is_array = True
            rest = rest[:start] + rest[end + 1:]
        rest = rest.strip()
        # Type code = first whitespace token (tolerates trailing `V(...)` etc.)
        code = rest.split()[0] if rest.split() else ""
        field = {"name": name, "is_array": is_array, "flags": flags}
        if code == "S":
            field["type"] = "string"
        elif code == "I":
            field["type"] = "integer"
        elif code == "F":
            field["type"] = "float"
        elif code == "B":
            field["type"] = "boolean"
        elif code.startswith("E(") and code.endswith(")"):
            field["type"] = "enum"
            field["values"] = [v.strip() for v in code[2:-1].split("|")]
        else:
            field["type"] = "unknown"
        schema["fields"].append(field)
    return schema
'''


_VALIDATE_VDL = '''
def validate_vdl_records(schema: dict, records: list) -> list:
    """Validate records against a parsed VDL schema.

    Returns one {"valid": bool, "errors": [str, ...]} result per record.
    Checks: required (R), nullability (N), type match, enum membership,
    and V(min..max) range constraints.
    """
    fields = []
    if isinstance(schema, dict):
        fields = schema.get("fields") or []
    results = []
    for record in (records or []):
        errors = []
        if not isinstance(record, dict):
            results.append({"valid": False, "errors": ["record is not an object"]})
            continue
        for field_def in fields:
            if not isinstance(field_def, dict):
                continue
            name = field_def.get("name", "")
            flags = field_def.get("flags") or []
            is_required = "R" in flags
            is_nullable = "N" in flags
            if name not in record:
                if is_required:
                    errors.append("missing required field: " + str(name))
                continue
            value = record[name]
            if value is None:
                if not is_nullable:
                    errors.append("field '%s' is not nullable" % name)
                continue
            expected_type = field_def.get("type", "unknown")
            if expected_type == "string" and not isinstance(value, str):
                errors.append("field '%s' expected string, got %s" % (name, type(value).__name__))
            elif expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
                errors.append("field '%s' expected integer, got %s" % (name, type(value).__name__))
            elif expected_type == "float" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                errors.append("field '%s' expected float, got %s" % (name, type(value).__name__))
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append("field '%s' expected boolean, got %s" % (name, type(value).__name__))
            elif expected_type == "enum":
                allowed = field_def.get("values") or []
                if value not in allowed:
                    errors.append("field '%s' value '%s' not in enum %s" % (name, value, allowed))
            for flag in flags:
                if isinstance(flag, str) and flag.startswith("V(") and flag.endswith(")"):
                    range_str = flag[2:-1]
                    if ".." in range_str:
                        lo, hi = range_str.split("..", 1)
                        try:
                            lo_val = float(lo) if lo else float("-inf")
                            hi_val = float(hi) if hi else float("inf")
                            if isinstance(value, (int, float)) and not isinstance(value, bool) \\
                                    and not (lo_val <= value <= hi_val):
                                errors.append("field '%s' value %s out of range [%s..%s]" % (name, value, lo, hi))
                        except (ValueError, TypeError):
                            pass
        results.append({"valid": len(errors) == 0, "errors": errors})
    return results
'''


REFERENCE_IMPLS = {
    "abr_binary_decode": {
        "session_id": "data_transform_s1",
        "task_id": "gap_1",
        "name": "decode_abr",
        "implementation": _DECODE_ABR,
    },
    "rle_decompress": {
        "session_id": "data_transform_s1",
        "task_id": "gap_2",
        "name": "decode_rle_matrix",
        "implementation": _DECODE_RLE,
    },
    "vdl_schema_parse": {
        "session_id": "data_transform_s2",
        "task_id": "gap_1",
        "name": "parse_vdl_schema",
        "implementation": _PARSE_VDL,
    },
    "vdl_record_validate": {
        "session_id": "data_transform_s2",
        "task_id": "gap_2",
        "name": "validate_vdl_records",
        "implementation": _VALIDATE_VDL,
    },
}
