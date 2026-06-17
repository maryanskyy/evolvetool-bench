import traceback
import sys
from io import StringIO

def parse_rle_matrix(data: str) -> str:
    """
    Parse RLE matrix format: 'rows,cols;value:count,value:count,...'
    Returns a string representation of a list of lists.
    """
    try:
        # Split dimensions from encoded data
        parts = data.split(';')
        if len(parts) != 2:
            raise ValueError("Invalid format: expected 'rows,cols;data'")
        
        dims = parts[0].split(',')
        if len(dims) != 2:
            raise ValueError("Invalid dimensions format")
        
        rows = int(dims[0])
        cols = int(dims[1])
        encoded_data = parts[1]
        
        # Parse the RLE encoded data
        elements = []
        runs = encoded_data.split(',')
        
        for run in runs:
            if ':' not in run:
                raise ValueError(f"Invalid run format: {run}")
            
            value_str, count_str = run.split(':')
            value = int(value_str)
            count = int(count_str)
            
            elements.extend([value] * count)
        
        # Validate total elements
        if len(elements) != rows * cols:
            raise ValueError(f"Element count {len(elements)} does not match matrix size {rows}x{cols}")
        
        # Reshape into matrix
        matrix = []
        for i in range(rows):
            row = elements[i * cols:(i + 1) * cols]
            matrix.append(row)
        
        return str(matrix)
    
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
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
        result = parse_rle_matrix('1,5;1:3,0:2')
        expected = '[[1, 1, 1, 0, 0]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_column():
    try:
        result = parse_rle_matrix('3,1;2:1,3:1,2:1')
        expected = '[[2], [3], [2]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_all_same_value():
    try:
        result = parse_rle_matrix('2,3;7:6')
        expected = '[[7, 7, 7], [7, 7, 7]]'
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_invalid_element_count():
    try:
        result = parse_rle_matrix('2,3;1:5')
        print(f"FAIL: Should have raised ValueError, got {result}")
    except ValueError:
        print("PASS")
    except Exception as e:
        print(f"FAIL: Wrong exception type: {str(e)}")

if __name__ == '__main__':
    test_basic_rle()
    test_single_row()
    test_single_column()
    test_all_same_value()
    test_invalid_element_count()