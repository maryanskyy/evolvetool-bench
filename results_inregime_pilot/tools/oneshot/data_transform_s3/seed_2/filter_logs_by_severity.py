def filter_logs_by_severity(logs_json_str, min_severity='WARN'):
    """
    Filters log records by severity level.
    
    Args:
        logs_json_str: JSON string containing list of log record dictionaries
        min_severity: Minimum severity level to include (default 'WARN')
    
    Returns:
        JSON string containing filtered log records
    """
    import json
    
    severity_levels = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4, 'FATAL': 4}
    min_level = severity_levels.get(min_severity.upper(), 2)
    
    logs = json.loads(logs_json_str)
    filtered = [log for log in logs if severity_levels.get(log.get('severity', 'INFO').upper(), 1) >= min_level]
    
    return json.dumps(filtered, indent=2)