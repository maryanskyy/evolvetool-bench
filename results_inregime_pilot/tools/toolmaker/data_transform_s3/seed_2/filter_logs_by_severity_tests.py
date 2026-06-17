import json
import sys
from io import StringIO

def filter_logs_by_severity(logs_json: str, min_severity: str = 'WARN') -> str:
    try:
        severity_levels = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3, 'CRITICAL': 4}
        
        logs = json.loads(logs_json)
        
        if not isinstance(logs, list):
            raise ValueError('Input must be a JSON array of log records')
        
        min_level = severity_levels.get(min_severity.upper())
        if min_level is None:
            raise ValueError(f'Unknown severity level: {min_severity}')
        
        filtered_logs = [
            log for log in logs
            if isinstance(log, dict) and 
            severity_levels.get(log.get('severity', '').upper(), -1) >= min_level
        ]
        
        return json.dumps(filtered_logs, indent=2)
    
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise

def test_filter_warn_and_above():
    logs_json = json.dumps([
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Server started on port 8080'},
        {'severity': 'INFO', 'subsystem': 2, 'message': 'Database connection established'},
        {'severity': 'WARN', 'subsystem': 3, 'message': 'Slow query detected: 1532ms'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection timeout to redis:6379'},
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Retrying connection attempt 1'},
        {'severity': 'ERROR', 'subsystem': 1, 'message': 'Connection failed after 3 retries'}
    ])
    
    result = filter_logs_by_severity(logs_json, 'WARN')
    filtered = json.loads(result)
    
    if len(filtered) == 3 and all(log['severity'] in ['WARN', 'ERROR'] for log in filtered):
        print('PASS')
    else:
        print(f'FAIL: Expected 3 records with WARN or ERROR, got {len(filtered)}')

def test_filter_error_only():
    logs_json = json.dumps([
        {'severity': 'INFO', 'subsystem': 1, 'message': 'Info message'},
        {'severity': 'WARN', 'subsystem': 2, 'message': 'Warning message'},
        {'severity': 'ERROR', 'subsystem': 3, 'message': 'Error message'},
        {'severity': 'CRITICAL', 'subsystem': 4, 'message': 'Critical message'}
    ])
    
    result = filter_logs_by_severity(logs_json, 'ERROR')
    filtered = json.loads(result)
    
    if len(filtered) == 2 and all(log['severity'] in ['ERROR', 'CRITICAL'] for log in filtered):
        print('PASS')
    else:
        print(f'FAIL: Expected 2 records with ERROR or CRITICAL, got {len(filtered)}')

def test_filter_all_below_threshold():
    logs_json = json.dumps([
        {'severity': 'DEBUG', 'subsystem': 1, 'message': 'Debug message'},
        {'severity': 'INFO', 'subsystem': 2, 'message': 'Info message'}
    ])
    
    result = filter_logs_by_severity(logs_json, 'WARN')
    filtered = json.loads(result)
    
    if len(filtered) == 0:
        print('PASS')
    else:
        print(f'FAIL: Expected 0 records, got {len(filtered)}')

def test_filter_empty_input():
    logs_json = json.dumps([])
    
    result = filter_logs_by_severity(logs_json, 'WARN')
    filtered = json.loads(result)
    
    if len(filtered) == 0:
        print('PASS')
    else:
        print(f'FAIL: Expected 0 records from empty input, got {len(filtered)}')

def test_filter_case_insensitive():
    logs_json = json.dumps([
        {'severity': 'warn', 'subsystem': 1, 'message': 'Warning'},
        {'severity': 'error', 'subsystem': 2, 'message': 'Error'},
        {'severity': 'info', 'subsystem': 3, 'message': 'Info'}
    ])
    
    result = filter_logs_by_severity(logs_json, 'warn')
    filtered = json.loads(result)
    
    if len(filtered) == 2 and all(log['severity'].lower() in ['warn', 'error'] for log in filtered):
        print('PASS')
    else:
        print(f'FAIL: Expected 2 records with case-insensitive matching, got {len(filtered)}')

if __name__ == '__main__':
    test_filter_warn_and_above()
    test_filter_error_only()
    test_filter_all_below_threshold()
    test_filter_empty_input()
    test_filter_case_insensitive()