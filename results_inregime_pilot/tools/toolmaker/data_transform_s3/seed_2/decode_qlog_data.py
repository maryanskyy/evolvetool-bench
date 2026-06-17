import base64
import json
import struct
import traceback
import sys

def decode_qlog_data(data: str) -> str:
    """
    Decodes base64-encoded QLOG data and returns parsed log records.
    
    Args:
        data: Base64-encoded string containing QLOG log record(s)
        
    Returns:
        JSON string containing parsed log records with timestamp, severity, and message
    """
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(data)
        
        # Parse the binary format
        # Format appears to be: 5 bytes timestamp + 3 bytes severity code + variable message
        if len(decoded_bytes) < 8:
            return json.dumps({"error": "Data too short to parse"})
        
        # Extract timestamp (first 5 bytes as big-endian)
        timestamp_bytes = decoded_bytes[0:5]
        timestamp_hex = timestamp_bytes.hex()
        
        # Extract severity code (next 3 bytes as big-endian integer)
        severity_bytes = decoded_bytes[5:8]
        severity_code = int.from_bytes(severity_bytes, byteorder='big')
        
        # Map severity codes to names
        severity_map = {
            24: "WARN",
            16: "INFO",
            32: "ERROR",
            8: "DEBUG"
        }
        severity_name = severity_map.get(severity_code, f"UNKNOWN({severity_code})")
        
        # Extract message (remaining bytes as UTF-8 string)
        message = decoded_bytes[8:].decode('utf-8', errors='replace')
        
        # Build result
        result = {
            "timestamp": timestamp_hex,
            "severity": severity_name,
            "message": message
        }
        
        return json.dumps(result)
        
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return json.dumps({"error": str(e)})