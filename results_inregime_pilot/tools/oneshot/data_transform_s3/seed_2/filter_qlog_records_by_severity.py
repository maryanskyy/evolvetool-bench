def filter_qlog_records_by_severity(records_json, min_severity='ERROR'):
    """
    Filters QLOG records by minimum severity level and returns matching records.
    
    Args:
        records_json: JSON string containing list of log record dictionaries
        min_severity: Minimum severity level to include ('ERROR', 'FATAL')
    
    Returns:
        JSON string containing filtered records and summary statistics
    """
    import json
    
    # Define severity hierarchy
    severity_levels = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3, 'FATAL': 4}
    min_level = severity_levels.get(min_severity, 3)
    
    # Parse input records
    try:
        records = json.loads(records_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({'error': 'Invalid JSON input', 'filtered_records': [], 'summary': {}})
    
    # Filter records
    filtered = []
    subsystem_errors = {}
    
    for record in records:
        if isinstance(record, dict):
            severity = record.get('severity', '')
            severity_level = severity_levels.get(severity, -1)
            
            if severity_level >= min_level:
                filtered.append(record)
                subsystem = record.get('subsystem')
                if subsystem is not None:
                    subsystem_errors[subsystem] = subsystem_errors.get(subsystem, 0) + 1
    
    # Build result
    result = {
        'filtered_records': filtered,
        'summary': {
            'total_records_processed': len(records),
            'filtered_records_count': len(filtered),
            'errors_by_subsystem': subsystem_errors
        }
    }
    
    return json.dumps(result, indent=2)