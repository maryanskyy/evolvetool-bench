import json
import sys
from io import StringIO

def filter_logs_by_severity(logs_json: str, min_severity: str = 'WARN') -> str:
    import json
    import traceback
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
        traceback.print_exc(file=sys.stderr)
        raise

def test_basic_filtering():
    logs_json = '[{"severity": "INFO", "subsystem": 1, "message": "Server started on port 8080"}, {"severity": "INFO", "subsystem": 2, "message": "Database connection established"}, {"severity": "WARN", "subsystem": 3, "message": "Slow query detected: 1532ms"}, {"severity": "ERROR", "subsystem": 1, "message": "Connection timeout to redis:6379"}, {"severity": "INFO", "subsystem": 1, "message": "Retrying connection attempt 1"}, {"severity": "ERROR", "subsystem": 1, "message": "Connection failed after 3 retries"}]'
    result = filter_logs_by_severity(logs_json)
    parsed = json.loads(result)
    
    if len(parsed) == 3 and all(log['severity'] in ['WARN', 'ERROR'] for log in parsed):
        print('PASS')
    else:
        print(f'FAIL: Expected 3 records with WARN or ERROR, got {len(parsed)}')

def test_all_info_logs():
    logs_json = '[{"severity": "INFO", "message": "msg1"}, {"severity": "INFO", "message": "msg2"}]'
    result = filter_logs_by_severity(logs_json)
    parsed = json.loads(result)
    
    if len(parsed) == 0:
        print('PASS')
    else:
        print(f'FAIL: Expected 0 records, got {len(parsed)}')

def test_all_error_logs():
    logs_json = '[{"severity": "ERROR", "message": "err1"}, {"severity": "CRITICAL", "message": "err2"}]'
    result = filter_logs_by_severity(logs_json)
    parsed = json.loads(result)
    
    if len(parsed) == 2 and all(log['severity'] in ['ERROR', 'CRITICAL'] for log in parsed):
        print('PASS')
    else:
        print(f'FAIL: Expected 2 records, got {len(parsed)}')

def test_custom_min_severity():
    logs_json = '[{"severity": "DEBUG", "message": "d"}, {"severity": "INFO", "message": "i"}, {"severity": "WARN", "message": "w"}, {"severity": "ERROR", "message": "e"}]'
    result = filter_logs_by_severity(logs_json, 'ERROR')
    parsed = json.loads(result)
    
    if len(parsed) == 1 and parsed[0]['severity'] == 'ERROR':
        print('PASS')
    else:
        print(f'FAIL: Expected 1 ERROR record, got {len(parsed)}')

def test_empty_logs():
    logs_json = '[]'
    result = filter_logs_by_severity(logs_json)
    parsed = json.loads(result)
    
    if len(parsed) == 0:
        print('PASS')
    else:
        print(f'FAIL: Expected 0 records, got {len(parsed)}')

if __name__ == '__main__':
    test_basic_filtering()
    test_all_info_logs()
    test_all_error_logs()
    test_custom_min_severity()
    test_empty_logs()