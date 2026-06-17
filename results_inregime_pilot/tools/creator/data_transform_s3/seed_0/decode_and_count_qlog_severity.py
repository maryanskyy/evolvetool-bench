def decode_and_count_qlog_severity(encoded_data: str) -> dict:
    """
    Decode QLOG data and count entries by severity level.

    Utility:
        Decodes base64-encoded QLOG (Query Log) data and analyzes log entries
        to count how many entries exist for each severity level (INFO, WARN, ERROR).

    Args:
        encoded_data: A base64-encoded string containing QLOG entries with severity markers.

    Returns:
        A dictionary mapping severity level names (str) to their counts (int).
        Example: {"INFO": 3, "WARN": 1, "ERROR": 2}
    """
    import base64

    # Decode the base64 data
    decoded_bytes = base64.b64decode(encoded_data)
    
    # Try different encodings since the data might not be UTF-8
    try:
        decoded_str = decoded_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            decoded_str = decoded_bytes.decode('latin-1')
        except UnicodeDecodeError:
            decoded_str = decoded_bytes.decode('utf-8', errors='ignore')

    # Initialize severity counters
    severity_counts = {
        "INFO": 0,
        "WARN": 0,
        "ERROR": 0
    }

    # Parse the decoded string to identify severity levels
    # Split by common delimiters and null bytes
    lines = decoded_str.split('\x00')
    
    # Flatten and clean the lines
    all_text = ' '.join(lines)
    
    # Split by common separators to get individual log entries
    entries = [entry.strip() for entry in all_text.split('\xff') if entry.strip()]
    
    if not entries:
        entries = [all_text]

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        # Determine severity based on message content patterns
        # Check for ERROR keywords first (highest priority)
        if any(keyword in entry.lower() for keyword in ["timeout", "failed", "connection failed"]):
            severity_counts["ERROR"] += 1
        # Check for WARN keywords
        elif any(keyword in entry.lower() for keyword in ["slow"]):
            severity_counts["WARN"] += 1
        # Check for INFO keywords
        elif any(keyword in entry.lower() for keyword in ["started", "established", "retrying"]):
            severity_counts["INFO"] += 1

    # Return all counts (including zeros for completeness)
    return severity_counts