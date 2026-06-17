def parse_rle_matrix_format(rle_string: str) -> str:
    """
    Parses RLE matrix format: 'rows,cols;val1:count1,val2:count2;val3:count3,...'
    Returns a string representation of the parsed matrix as a list of lists.
    """
    parts = rle_string.split(';')
    dims = parts[0].split(',')
    rows = int(dims[0])
    cols = int(dims[1])
    
    # Parse the RLE data
    rle_data = parts[1]
    elements = []
    
    for pair in rle_data.split(','):
        if ':' in pair:
            val, count = pair.split(':')
            val = int(val)
            count = int(count)
            elements.extend([val] * count)
        else:
            elements.append(int(pair))
    
    # Build the matrix
    matrix = []
    for i in range(rows):
        row = elements[i * cols:(i + 1) * cols]
        matrix.append(row)
    
    return str(matrix)