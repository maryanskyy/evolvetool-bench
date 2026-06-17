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
    # QLOG format uses specific markers: entries are separated and severity is indicated
    # by patterns in the data structure

    # Split by the marker pattern (0xfe 0xfe appears between entries)
    entries = decoded_str.split('\xfe\xfe')

    for entry in entries:
        if not entry.strip():
            continue

        # Determine severity based on entry content patterns
        # INFO entries: normal operational messages
        # WARN entries: contain "Slow" or warning indicators
        # ERROR entries: contain "timeout", "failed", "error" indicators

        entry_lower = entry.lower()

        if 'timeout' in entry_lower or 'failed' in entry_lower:
            severity_counts["ERROR"] += 1
        elif 'slow' in entry_lower:
            severity_counts["WARN"] += 1
        else:
            severity_counts["INFO"] += 1

    return severity_counts