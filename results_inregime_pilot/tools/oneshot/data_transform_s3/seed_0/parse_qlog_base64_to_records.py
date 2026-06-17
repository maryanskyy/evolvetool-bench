def parse_qlog_base64_to_records(base64_data: str) -> str:
    import base64
    import struct
    from datetime import datetime
    
    try:
        binary_data = base64.b64decode(base64_data)
    except Exception as e:
        return f"Error decoding base64: {e}"
    
    if len(binary_data) < 8:
        return "Error: Binary data too short"
    
    severity_map = {0: "INFO", 1: "WARN", 2: "ERROR", 3: "CRITICAL"}
    subsystem_map = {7: "Disk", 1: "Network", 2: "Memory", 3: "CPU"}
    
    try:
        severity = binary_data[0]
        subsystem = binary_data[1]
        timestamp_ms = struct.unpack('>I', binary_data[2:6])[0]
        message_bytes = binary_data[6:]
        message = message_bytes.decode('utf-8', errors='ignore')
        
        severity_str = severity_map.get(severity, f"UNKNOWN({severity})")
        subsystem_str = subsystem_map.get(subsystem, str(subsystem))
        
        dt = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
        timestamp_str = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        result = f"Severity: {severity_str}\nSubsystem: {subsystem_str}\nTimestamp: {timestamp_str}\nMessage: {message}"
        return result
    except Exception as e:
        return f"Error parsing binary data: {e}"