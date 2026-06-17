def filter_logs_by_severity(log_records, min_severity='WARN'):
    """
    Filter parsed log records to include only entries at or above a specified severity level.
    
    Utility:
        Filters log records based on severity levels, keeping only records that meet or exceed
        the minimum severity threshold. Useful for identifying important issues in log data.
    
    Args:
        log_records (list): List of dictionaries containing log records with 'severity' key.
                           Each record should have at least a 'severity' field.
        min_severity (str): Minimum severity level to include. Valid values are 'INFO', 'WARN',
                           'ERROR', 'CRITICAL' (default: 'WARN').
    
    Returns:
        list: Filtered list of log record dictionaries containing only records with severity
              at or above the specified minimum level, ordered by severity importance.
    """
    severity_levels = {
        'INFO': 0,
        'WARN': 1,
        'ERROR': 2,
        'CRITICAL': 3
    }
    
    if min_severity not in severity_levels:
        raise ValueError(f"Invalid severity level: {min_severity}. Must be one of {list(severity_levels.keys())}")
    
    min_level = severity_levels[min_severity]
    
    filtered_records = [
        record for record in log_records
        if severity_levels.get(record.get('severity', 'INFO'), 0) >= min_level
    ]
    
    return filtered_records


if __name__ == '__main__':
    log_data = [
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Server started on port 8080'},
        {'severity': 'INFO', 'subsystem': 2, 'message': 'Database connection established'},
        {'severity': 'WARN', 'subsystem': 3, 'message': 'Slow query detected: 1532ms'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection timeout to redis:6379'},
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Retrying connection attempt 1'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection failed after 3 retries'}
    ]
    
    result = filter_logs_by_severity(log_data, 'WARN')
    for record in result:
        print(record)