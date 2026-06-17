def filter_qlog_records_by_severity(records, min_severity='ERROR'):
    """
    Filter and aggregate parsed QLOG records by severity level.
    
    Utility:
        Filters log records to include only entries with a specified minimum severity
        level or higher. Severity levels are ordered: DEBUG < INFO < WARN < ERROR < FATAL.
        Returns filtered records along with aggregation statistics.
    
    Args:
        records (list): List of dictionaries containing log records with keys:
                       'severity', 'subsystem', and 'message'
        min_severity (str): Minimum severity level to include. Valid values are:
                           'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'.
                           Default is 'ERROR'.
    
    Returns:
        dict: A dictionary containing:
              - 'filtered_records': List of filtered log records
              - 'total_filtered': Count of records matching the filter
              - 'total_original': Count of original records
              - 'affected_subsystems': Set of subsystem IDs in filtered records
              - 'severity_breakdown': Count of each severity level in filtered records
    """
    severity_levels = {
        'DEBUG': 0,
        'INFO': 1,
        'WARN': 2,
        'ERROR': 3,
        'FATAL': 4
    }
    
    if min_severity not in severity_levels:
        raise ValueError(f"Invalid severity level: {min_severity}")
    
    min_level = severity_levels[min_severity]
    
    filtered_records = [
        record for record in records
        if severity_levels.get(record.get('severity', 'DEBUG'), 0) >= min_level
    ]
    
    affected_subsystems = set(
        record.get('subsystem') for record in filtered_records
    )
    
    severity_breakdown = {}
    for record in filtered_records:
        severity = record.get('severity', 'UNKNOWN')
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
    
    return {
        'filtered_records': filtered_records,
        'total_filtered': len(filtered_records),
        'total_original': len(records),
        'affected_subsystems': sorted(list(affected_subsystems)),
        'severity_breakdown': severity_breakdown
    }