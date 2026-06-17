def parse_rle_matrix_with_dimensions(rle_string):
    """
    Parse RLE matrix format: dimensions;rle_data
    Example: '3,4;0:4,-1:2,0:2,999:1,0:3'
    Returns string representation of list of lists.
    """
    parts = rle_string.split(';')
    dims = parts[0].split(',')
    rows = int(dims[0])
    cols = int(dims[1])
    
    rle_data = parts[1]
    runs = rle_data.split(',')
    
    # Expand RLE into flat list
    flat_list = []
    for run in runs:
        if ':' in run:
            value_str, count_str = run.split(':')
            value = int(value_str)
            count = int(count_str)
            flat_list.extend([value] * count)
        else:
            flat_list.append(int(run))
    
    # Convert flat list to matrix (list of lists)
    matrix = []
    for i in range(rows):
        row = flat_list[i * cols:(i + 1) * cols]
        matrix.append(row)
    
    return str(matrix)