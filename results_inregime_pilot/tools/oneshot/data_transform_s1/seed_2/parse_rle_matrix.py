def parse_rle_matrix(rle_string):
    """
    Parse Run-Length Encoded matrix format and reconstruct the matrix.
    Format: 'rows,cols;val:count,val:count,...'
    Returns the matrix as a JSON string representation of a list of lists.
    """
    # Split the input into dimensions and encoded data
    parts = rle_string.split(';')
    dims = parts[0].split(',')
    rows = int(dims[0])
    cols = int(dims[1])
    
    # Parse the RLE data
    rle_data = parts[1].split(',')
    
    # Expand the RLE into a flat list
    flat_list = []
    for item in rle_data:
        val, count = item.split(':')
        val = int(val)
        count = int(count)
        flat_list.extend([val] * count)
    
    # Reshape into matrix (list of lists)
    matrix = []
    for i in range(rows):
        row = flat_list[i * cols:(i + 1) * cols]
        matrix.append(row)
    
    # Convert to JSON string for return
    import json
    return json.dumps(matrix)