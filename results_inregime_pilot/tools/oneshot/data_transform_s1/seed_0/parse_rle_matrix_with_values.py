def parse_rle_matrix_with_values(rle_string):
    """
    Parses RLE matrix format: dimensions;value:count,value:count,...
    Returns a string representation of the matrix as a list of lists.
    """
    parts = rle_string.split(';')
    dims = parts[0].split(',')
    rows = int(dims[0])
    cols = int(dims[1])
    
    # Parse the RLE data
    rle_data = parts[1]
    runs = rle_data.split(',')
    
    # Expand the RLE into a flat list
    flat_list = []
    for run in runs:
        if ':' in run:
            value_str, count_str = run.split(':')
            value = int(value_str)
            count = int(count_str)
            flat_list.extend([value] * count)
        else:
            # Handle edge case of single value without count
            flat_list.append(int(run))
    
    # Reshape into matrix
    matrix = []
    for i in range(rows):
        row = flat_list[i * cols:(i + 1) * cols]
        matrix.append(row)
    
    return str(matrix)