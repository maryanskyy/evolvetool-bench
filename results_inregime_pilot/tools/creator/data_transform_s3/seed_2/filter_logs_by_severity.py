def filter_logs_by_severity(logs, min_severity='WARN'):
    """
    Filter parsed log records to include only entries at or above a specified severity level.
    
    Utility:
        Filters log records based on severity level, useful for identifying important events
        (warnings, errors, critical issues) while filtering out verbose info/debug messages.
    
    Args:
        logs (list): List of log record dictionaries, each containing 'severity', 'subsystem', 
                     and 'message' keys.
        min_severity (str): Minimum severity level to include. Valid levels in order of 
                           increasing severity: 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'.
                           Default is 'WARN'.
    
    Returns:
        list: Filtered list of log records that meet or exceed the minimum severity threshold.
    """
    severity_levels = {
        'DEBUG': 0,
        'INFO': 1,
        'WARN': 2,
        'ERROR': 3,
        'CRITICAL': 4
    }
    
    min_level = severity_levels.get(min_severity.upper(), 2)
    
    filtered_logs = [
        log for log in logs 
        if severity_levels.get(log.get('severity', 'INFO').upper(), 1) >= min_level
    ]
    
    return filtered_logs


if __name__ == '__main__':
    logs = [
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Server started on port 8080'},
        {'severity': 'INFO', 'subsystem': 2, 'message': 'Database connection established'},
        {'severity': 'WARN', 'subsystem': 3, 'message': 'Slow query detected: 1532ms'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection timeout to redis:6379'},
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Retrying connection attempt 1'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection failed after 3 retries'}
    ]
    
    result = filter_logs_by_severity(logs, 'WARN')
    for log in result:
        print(log)