def filter_logs_by_severity(logs_json_str):
    import json
    
    severity_order = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4, 'FATAL': 4}
    min_severity_level = severity_order.get('WARN', 2)
    
    try:
        logs = json.loads(logs_json_str)
    except (json.JSONDecodeError, TypeError):
        return json.dumps([])
    
    if not isinstance(logs, list):
        return json.dumps([])
    
    filtered = []
    for record in logs:
        if isinstance(record, dict) and 'severity' in record:
            severity = record['severity'].upper()
            if severity_order.get(severity, -1) >= min_severity_level:
                filtered.append(record)
    
    return json.dumps(filtered)