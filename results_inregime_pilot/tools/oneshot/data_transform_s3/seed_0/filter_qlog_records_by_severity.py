def filter_qlog_records_by_severity(records_json, min_severity='ERROR'):
    """
    Filters QLOG records by minimum severity level and returns matching records.
    
    Args:
        records_json: JSON string containing parsed QLOG records
        min_severity: Minimum severity level to include ('ERROR', 'FATAL')
    
    Returns:
        JSON string containing filtered records and summary statistics
    """
    import json
    
    # Parse input JSON
    records = json.loads(records_json)
    
    # Define severity hierarchy
    severity_levels = {'INFO': 0, 'WARN': 1, 'ERROR': 2, 'FATAL': 3}
    min_level = severity_levels.get(min_severity, 2)
    
    # Filter records
    filtered = [r for r in records if severity_levels.get(r.get('severity', 'INFO'), 0) >= min_level]
    
    # Calculate statistics
    total_records = len(records)
    filtered_count = len(filtered)
    subsystems_affected = set(r.get('subsystem') for r in filtered)
    
    # Build result
    result = {
        'filtered_records': filtered,
        'summary': {
            'total_records_processed': total_records,
            'filtered_records_count': filtered_count,
            'subsystems_affected': sorted(list(subsystems_affected))
        }
    }
    
    return json.dumps(result, indent=2)