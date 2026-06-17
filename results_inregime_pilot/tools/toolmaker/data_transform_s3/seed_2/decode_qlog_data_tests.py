import json
import sys
import base64

def decode_qlog_data(data: str) -> str:
    import traceback
    try:
        decoded_bytes = base64.b64decode(data)
        
        if len(decoded_bytes) < 8:
            return json.dumps({"error": "Data too short to parse"})
        
        timestamp_bytes = decoded_bytes[0:5]
        timestamp_hex = timestamp_bytes.hex()
        
        severity_bytes = decoded_bytes[5:8]
        severity_code = int.from_bytes(severity_bytes, byteorder='big')
        
        severity_map = {
            24: "WARN",
            16: "INFO",
            32: "ERROR",
            8: "DEBUG"
        }
        severity_name = severity_map.get(severity_code, f"UNKNOWN({severity_code})")
        
        message = decoded_bytes[8:].decode('utf-8', errors='replace')
        
        result = {
            "timestamp": timestamp_hex,
            "severity": severity_name,
            "message": message
        }
        
        return json.dumps(result)
        
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return json.dumps({"error": str(e)})

# Test 1: Original provided data
try:
    result = decode_qlog_data("APM8wDcAABhEaXNrIHVzYWdlIGF0IDg1IHBlcmNlbnQ=")
    parsed = json.loads(result)
    assert "timestamp" in parsed
    assert "severity" in parsed
    assert "message" in parsed
    assert parsed["severity"] == "WARN"
    assert "Disk usage at 85 percent" in parsed["message"]
    print("PASS")
except AssertionError as e:
    print(f"FAIL: Assertion failed - {e}")
except Exception as e:
    print(f"FAIL: {e}")

# Test 2: Invalid base64 data
try:
    result = decode_qlog_data("!!!invalid!!!")
    parsed = json.loads(result)
    assert "error" in parsed
    print("PASS")
except Exception as e:
    print(f"FAIL: {e}")

# Test 3: Empty string
try:
    result = decode_qlog_data("")
    parsed = json.loads(result)
    assert "error" in parsed
    print("PASS")
except Exception as e:
    print(f"FAIL: {e}")

# Test 4: Data too short (less than 8 bytes)
try:
    short_data = base64.b64encode(b"\x00\x01\x02").decode()
    result = decode_qlog_data(short_data)
    parsed = json.loads(result)
    assert "error" in parsed
    assert "too short" in parsed["error"]
    print("PASS")
except Exception as e:
    print(f"FAIL: {e}")

# Test 5: Valid data with INFO severity
try:
    test_data = b"\x00\x11\x22\x33\x44\x00\x00\x10Test info message"
    encoded = base64.b64encode(test_data).decode()
    result = decode_qlog_data(encoded)
    parsed = json.loads(result)
    assert parsed["severity"] == "INFO"
    assert "Test info message" in parsed["message"]
    print("PASS")
except Exception as e:
    print(f"FAIL: {e}")