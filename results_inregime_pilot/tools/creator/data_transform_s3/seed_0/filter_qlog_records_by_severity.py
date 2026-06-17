def filter_qlog_records_by_severity(records, min_severity='ERROR'):
    """
    Filter and aggregate parsed QLOG records by severity level.
    
    Utility:
        Filters log records to include only entries with specified severity level
        or higher. Severity levels are ordered: INFO < WARN < ERROR < FATAL.
        Returns filtered records and provides aggregation statistics.
    
    Args:
        records (list): List of dictionaries containing log records with keys:
                       'severity', 'subsystem', and 'message'
        min_severity (str): Minimum severity level to include. Valid values are
                           'INFO', 'WARN', 'ERROR', 'FATAL'. Default is 'ERROR'.
    
    Returns:
        dict: Contains 'filtered_records' (list of matching records),
              'total_filtered' (count of filtered records),
              'total_original' (count of original records),
              'subsystems_affected' (list of unique subsystem IDs in filtered results)
    """
    severity_levels = {
        'INFO': 0,
        'WARN': 1,
        'ERROR': 2,
        'FATAL': 3
    }
    
    if min_severity not in severity_levels:
        raise ValueError(f"Invalid severity level: {min_severity}")
    
    min_level = severity_levels[min_severity]
    
    filtered = [
        record for record in records
        if severity_levels.get(record.get('severity', 'INFO'), 0) >= min_level
    ]
    
    subsystems_affected = sorted(set(
        record.get('subsystem') for record in filtered
        if record.get('subsystem') is not None
    ))
    
    return {
        'filtered_records': filtered,
        'total_filtered': len(filtered),
        'total_original': len(records),
        'subsystems_affected': subsystems_affected,
        'min_severity_filter': min_severity
    }