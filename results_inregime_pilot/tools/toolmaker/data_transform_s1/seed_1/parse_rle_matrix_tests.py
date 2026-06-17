import traceback
import sys
from io import StringIO

def parse_rle_matrix(data: str) -> str:
    """
    Parse RLE matrix format: 'rows,cols;value:count,value:count,...'
    Returns string representation of list of lists.
    """
    try:
        # Split header from data
        parts = data.split(';')
        if len(parts) != 2:
            raise ValueError("Invalid format: expected 'rows,cols;encoded_data'")
        
        header = parts[0]
        encoded_data = parts[1]
        
        # Parse dimensions
        dims = header.split(',')
        if len(dims) != 2:
            raise ValueError("Invalid header: expected 'rows,cols'")
        
        rows = int(dims[0])
        cols = int(dims[1])
        
        # Parse RLE data
        elements = []
        runs = encoded_data.split(',')
        
        for run in runs:
            parts = run.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid run format: expected 'value:count', got '{run}'")
            
            value = int(parts[0])
            count = int(parts[1])
            elements.extend([value] * count)
        
        # Validate total elements
        expected_total = rows * cols
        if len(elements) != expected_total:
            raise ValueError(f"Element count mismatch: got {len(elements)}, expected {expected_total}")
        
        # Reshape into matrix
        matrix = []
        for i in range(rows):
            row = elements[i * cols:(i + 1) * cols]
            matrix.append(row)
        
        return str(matrix)
    
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        raise

# Test suite
def test_basic_rle():
    try:
        result = parse_rle_matrix('2,6;5:2,0:7,5:3')
        expected = '[[5, 5, 0, 0, 0, 0], [0, 0, 0, 5, 5, 5]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_row():
    try:
        result = parse_rle_matrix('1,5;1:3,2:2')
        expected = '[[1, 1, 1, 2, 2]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_column():
    try:
        result = parse_rle_matrix('3,1;7:1,8:1,9:1')
        expected = '[[7], [8], [9]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_all_same_value():
    try:
        result = parse_rle_matrix('2,3;5:6')
        expected = '[[5, 5, 5], [5, 5, 5]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_element_count_mismatch():
    try:
        result = parse_rle_matrix('2,3;5:2,0:2')
        print(f"FAIL: Should have raised ValueError for element count mismatch")
    except ValueError as e:
        if "Element count mismatch" in str(e):
            print("PASS")
        else:
            print(f"FAIL: Wrong error message: {str(e)}")
    except Exception as e:
        print(f"FAIL: Unexpected exception: {str(e)}")

if __name__ == '__main__':
    test_basic_rle()
    test_single_row()
    test_single_column()
    test_all_same_value()
    test_element_count_mismatch()