def parse_rle_matrix(rle_string):
    """
    Parses Run-Length Encoded matrix format and reconstructs the matrix.
    Format: 'rows,cols;val:count,val:count,...'
    Returns the matrix as a JSON string representation of a list of lists.
    """
    # Split the input into dimensions and encoded data
    parts = rle_string.split(';')
    dims = parts[0].split(',')
    rows = int(dims[0])
    cols = int(dims[1])
    
    # Parse the RLE data
    encoded_data = parts[1].split(',')
    
    # Expand the RLE into a flat list
    flat_list = []
    for item in encoded_data:
        val, count = item.split(':')
        val = int(val)
        count = int(count)
        flat_list.extend([val] * count)
    
    # Reshape into matrix (rows x cols)
    matrix = []
    for i in range(rows):
        row = flat_list[i * cols:(i + 1) * cols]
        matrix.append(row)
    
    # Return as JSON string
    import json
    return json.dumps(matrix)