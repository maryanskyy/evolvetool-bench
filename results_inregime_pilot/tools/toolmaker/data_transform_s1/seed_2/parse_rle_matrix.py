import traceback
import sys

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