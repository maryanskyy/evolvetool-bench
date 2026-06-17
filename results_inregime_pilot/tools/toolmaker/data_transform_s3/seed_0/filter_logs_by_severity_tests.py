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
        
        filtered_logs = []
        for log in logs:
            if not isinstance(log, dict):
                continue
            
            log_severity = log.get('severity', '').upper()
            log_level = severity_levels.get(log_severity)
            
            if log_level is not None and log_level >= min_level:
                filtered_logs.append(log)
        
        return json.dumps(filtered_logs, indent=2)
    
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise

def test_filter_logs_basic():
    logs_json = '[{"severity": "INFO", "subsystem": 1, "message": "Server started on port 8080"}, {"severity": "INFO", "subsystem": 2, "message": "Database connection established"}, {"severity": "WARN", "subsystem": 3, "message": "Slow query detected: 1532ms"}, {"severity": "ERROR", "subsystem": 1, "message": "Connection timeout to redis:6379"}, {"severity": "INFO", "subsystem": 1, "message": "Retrying connection attempt 1"}, {"severity": "ERROR", "subsystem": 1, "message": "Connection failed after 3 retries"}]'
    result = filter_logs_by_severity(logs_json)
    filtered = json.loads(result)
    
    if len(filtered) == 3 and all(log['severity'] in ['WARN', 'ERROR'] for log in filtered):
        print('PASS')
    else:
        print(f'FAIL: Expected 3 records with WARN or ERROR, got {len(filtered)}')

def test_filter_logs_all_info():
    logs_json = '[{"severity": "INFO", "subsystem": 1, "message": "msg1"}, {"severity": "INFO", "subsystem": 2, "message": "msg2"}]'
    result = filter_logs_by_severity(logs_json)
    filtered = json.loads(result)
    
    if len(filtered) == 0:
        print('PASS')
    else:
        print(f'FAIL: Expected 0 records, got {len(filtered)}')

def test_filter_logs_all_error():
    logs_json = '[{"severity": "ERROR", "subsystem": 1, "message": "err1"}, {"severity": "CRITICAL", "subsystem": 2, "message": "err2"}]'
    result = filter_logs_by_severity(logs_json)
    filtered = json.loads(result)
    
    if len(filtered) == 2 and all(log['severity'] in ['ERROR', 'CRITICAL'] for log in filtered):
        print('PASS')
    else:
        print(f'FAIL: Expected 2 records, got {len(filtered)}')

def test_filter_logs_custom_severity():
    logs_json = '[{"severity": "DEBUG", "subsystem": 1, "message": "debug"}, {"severity": "INFO", "subsystem": 2, "message": "info"}, {"severity": "WARN", "subsystem": 3, "message": "warn"}]'
    result = filter_logs_by_severity(logs_json, 'INFO')
    filtered = json.loads(result)
    
    if len(filtered) == 2 and all(log['severity'] in ['INFO', 'WARN'] for log in filtered):
        print('PASS')
    else:
        print(f'FAIL: Expected 2 records with INFO or above, got {len(filtered)}')

def test_filter_logs_empty():
    logs_json = '[]'
    result = filter_logs_by_severity(logs_json)
    filtered = json.loads(result)
    
    if len(filtered) == 0:
        print('PASS')
    else:
        print(f'FAIL: Expected 0 records from empty input, got {len(filtered)}')

if __name__ == '__main__':
    test_filter_logs_basic()
    test_filter_logs_all_info()
    test_filter_logs_all_error()
    test_filter_logs_custom_severity()
    test_filter_logs_empty()