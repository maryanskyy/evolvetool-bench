import sys
import traceback

def parse_rle_matrix(data: str) -> str:
    """
    Parse Run-Length Encoded matrix format and reconstruct the matrix.
    Format: 'rows,cols;val:count,val:count,...'
    Returns the matrix as a string representation of a list of lists.
    """
    try:
        # Split the input into dimensions and RLE data
        parts = data.split(';')
        if len(parts) != 2:
            raise ValueError("Invalid format: expected 'rows,cols;val:count,...'")
        
        dims = parts[0].split(',')
        if len(dims) != 2:
            raise ValueError("Invalid dimensions: expected 'rows,cols'")
        
        rows = int(dims[0])
        cols = int(dims[1])
        total_elements = rows * cols
        
        # Parse the RLE data
        rle_pairs = parts[1].split(',')
        flat_list = []
        
        for pair in rle_pairs:
            val_count = pair.split(':')
            if len(val_count) != 2:
                raise ValueError(f"Invalid RLE pair: {pair}")
            
            val = int(val_count[0])
            count = int(val_count[1])
            flat_list.extend([val] * count)
        
        # Validate total elements
        if len(flat_list) != total_elements:
            raise ValueError(f"Expected {total_elements} elements, got {len(flat_list)}")
        
        # Reshape into matrix
        matrix = []
        for i in range(rows):
            row = flat_list[i * cols:(i + 1) * cols]
            matrix.append(row)
        
        return str(matrix)
    
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise

# Test Suite
def test_basic_example():
    try:
        result = parse_rle_matrix("3,5;1:3,0:4,2:3,3:5")
        expected = "[[1, 1, 1, 0, 0], [0, 0, 2, 2, 2], [3, 3, 3, 3, 3]]"
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_row():
    try:
        result = parse_rle_matrix("1,4;5:2,7:2")
        expected = "[[5, 5, 7, 7]]"
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_column():
    try:
        result = parse_rle_matrix("4,1;2:4")
        expected = "[[2], [2], [2], [2]]"
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_single_element():
    try:
        result = parse_rle_matrix("1,1;9:1")
        expected = "[[9]]"
        if result == expected:
            print("PASS")
        else:
            print(f"FAIL: Expected {expected}, got {result}")
    except Exception as e:
        print(f"FAIL: {str(e)}")

def test_invalid_format():
    try:
        result = parse_rle_matrix("3,5;1:3,0:4,2:3")
        print(f"FAIL: Should have raised ValueError for mismatched element count")
    except ValueError:
        print("PASS")
    except Exception as e:
        print(f"FAIL: Unexpected exception: {str(e)}")

if __name__ == "__main__":
    test_basic_example()
    test_single_row()
    test_single_column()
    test_single_element()
    test_invalid_format()