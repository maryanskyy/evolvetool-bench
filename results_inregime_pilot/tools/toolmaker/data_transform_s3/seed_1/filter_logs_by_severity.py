import json
import traceback
from typing import List, Dict, Any

def filter_logs_by_severity(logs_json: str, min_severity: str = 'WARN') -> str:
    """
    Filters log records by minimum severity level.
    
    Args:
        logs_json: JSON string containing list of log record dictionaries
        min_severity: Minimum severity level to include (default: 'WARN')
    
    Returns:
        JSON string containing filtered log records
    """
    try:
        severity_levels = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}
        
        logs = json.loads(logs_json)
        
        if not isinstance(logs, list):
            raise ValueError('Input must be a JSON array of log records')
        
        min_level = severity_levels.get(min_severity.upper())
        if min_level is None:
            raise ValueError(f'Unknown severity level: {min_severity}')
        
        filtered = []
        for log in logs:
            if not isinstance(log, dict):
                continue
            
            log_severity = log.get('severity', '').upper()
            log_level = severity_levels.get(log_severity)
            
            if log_level is not None and log_level >= min_level:
                filtered.append(log)
        
        return json.dumps(filtered, indent=2)
    
    except Exception as e:
        import sys
        traceback.print_exc(file=sys.stderr)
        raise