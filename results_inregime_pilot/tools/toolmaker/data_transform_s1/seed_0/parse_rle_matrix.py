import traceback

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
        import sys
        sys.stderr.write(traceback.format_exc())
        raise