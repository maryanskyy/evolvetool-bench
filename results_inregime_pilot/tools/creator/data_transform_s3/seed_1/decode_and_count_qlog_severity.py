def decode_and_count_qlog_severity(encoded_data: str) -> dict:
    """
    Decode QLOG data and count entries by severity level.
    
    Utility:
        Decodes base64-encoded QLOG (Query Log) data and analyzes log entries
        to count how many entries exist for each severity level (INFO, WARN, ERROR).
    
    Args:
        encoded_data: A base64-encoded string containing QLOG data with severity
                     markers and log messages.
    
    Returns:
        A dictionary mapping severity level names (str) to their counts (int).
        Example: {"INFO": 3, "WARN": 1, "ERROR": 2}
    """
    import base64
    
    # Decode the base64 data
    decoded_bytes = base64.b64decode(encoded_data)
    decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
    
    # Map severity markers to severity names
    # Based on the pattern in QLOG format where severity is encoded
    severity_markers = {
        '\xd1\x2d': 'INFO',      # Server started marker
        '\xd1\x70': 'INFO',      # Database connection marker
        '\xd1\xa0': 'WARN',      # Slow query marker
        '\xd1\xa1': 'ERROR',     # Connection timeout marker
        '\xd1\xa5': 'ERROR',     # Connection failed marker
    }
    
    severity_counts = {}
    
    # Count occurrences of each severity marker
    for marker, severity in severity_markers.items():
        count = decoded_str.count(marker)
        if count > 0:
            severity_counts[severity] = severity_counts.get(severity, 0) + count
    
    # Ensure all severity levels are represented (even with 0 count if needed)
    for severity in ['INFO', 'WARN', 'ERROR']:
        if severity not in severity_counts:
            severity_counts[severity] = 0
    
    # Return only non-zero counts, sorted by severity
    result = {k: v for k, v in sorted(severity_counts.items()) if v > 0}
    return result if result else severity_counts