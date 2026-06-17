def decode_qlog_data(encoded_data: str) -> list:
    """
    Decode QLOG (Query Log) data from base64 format and parse log records.
    
    Utility:
        Decodes base64-encoded QLOG data and extracts structured log records
        containing severity level, subsystem ID, timestamp, and message content.
    
    Args:
        encoded_data (str): Base64-encoded QLOG data string
    
    Returns:
        list: List of dictionaries containing parsed log records with keys:
              - severity (str): Log level (INFO, WARN, ERROR, etc.)
              - subsystem (int): Subsystem identifier
              - timestamp (str): ISO 8601 formatted timestamp
              - message (str): Log message text
    """
    import base64
    import struct
    from datetime import datetime
    
    # Decode base64 data
    decoded_bytes = base64.b64decode(encoded_data)
    
    # Parse binary format
    # Format: 4 bytes version/flags, 4 bytes timestamp, 1 byte severity, 1 byte subsystem, rest is message
    if len(decoded_bytes) < 10:
        return []
    
    # Extract fields
    version_flags = struct.unpack('>I', decoded_bytes[0:4])[0]
    timestamp_seconds = struct.unpack('>I', decoded_bytes[4:8])[0]
    severity_byte = decoded_bytes[8]
    subsystem_byte = decoded_bytes[9]
    message_bytes = decoded_bytes[10:]
    
    # Decode message
    message = message_bytes.decode('utf-8', errors='replace')
    
    # Map severity byte to severity name
    severity_map = {
        0: "DEBUG",
        1: "INFO",
        2: "WARN",
        3: "ERROR",
        4: "CRITICAL"
    }
    severity = severity_map.get(severity_byte, "UNKNOWN")
    
    # Convert timestamp to ISO 8601 format
    timestamp = datetime.utcfromtimestamp(timestamp_seconds).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Create log record
    log_record = {
        "severity": severity,
        "subsystem": subsystem_byte,
        "timestamp": timestamp,
        "message": message
    }
    
    return [log_record]