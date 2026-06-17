import traceback

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
        import sys
        print(traceback.format_exc(), file=sys.stderr)
        raise