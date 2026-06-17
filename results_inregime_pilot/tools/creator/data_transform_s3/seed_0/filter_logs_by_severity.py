def filter_logs_by_severity(logs, min_severity='WARN'):
    """
    Filter parsed log records to include only entries at or above a specified severity level.
    
    Utility:
        Filters log records based on severity level, useful for identifying important events
        like warnings and errors while excluding informational messages.
    
    Args:
        logs (list): List of log record dictionaries, each containing 'severity', 'subsystem',
                     and 'message' keys.
        min_severity (str): Minimum severity level to include. Valid levels in order:
                           'INFO', 'WARN', 'ERROR', 'CRITICAL'. Defaults to 'WARN'.
    
    Returns:
        list: Filtered list of log records that meet or exceed the minimum severity level.
    """
    severity_levels = {
        'INFO': 0,
        'WARN': 1,
        'ERROR': 2,
        'CRITICAL': 3
    }
    
    if min_severity not in severity_levels:
        raise ValueError(f"Invalid severity level: {min_severity}")
    
    min_level = severity_levels[min_severity]
    
    filtered_logs = [
        log for log in logs
        if severity_levels.get(log.get('severity', 'INFO'), 0) >= min_level
    ]
    
    return filtered_logs


# Test with the provided data
if __name__ == '__main__':
    log_records = [
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Server started on port 8080'},
        {'severity': 'INFO', 'subsystem': 2, 'message': 'Database connection established'},
        {'severity': 'WARN', 'subsystem': 3, 'message': 'Slow query detected: 1532ms'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection timeout to redis:6379'},
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Retrying connection attempt 1'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection failed after 3 retries'}
    ]
    
    result = filter_logs_by_severity(log_records, 'WARN')
    print(result)