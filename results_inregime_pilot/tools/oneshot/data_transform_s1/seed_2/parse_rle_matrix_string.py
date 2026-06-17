def parse_rle_matrix_string(rle_data):
    import json
    
    # Split by semicolon to separate dimensions from data
    parts = rle_data.split(';')
    
    # Parse dimensions
    dims = list(map(int, parts[0].split(',')))
    rows, cols = dims[0], dims[1]
    
    # Parse RLE data
    rle_part = parts[1] if len(parts) > 1 else ""
    
    # Decode RLE format: value:count pairs
    decoded_values = []
    
    if rle_part:
        pairs = rle_part.split(',')
        for pair in pairs:
            if ':' in pair:
                value_str, count_str = pair.split(':')
                value = int(value_str)
                count = int(count_str)
                # Add 'count' repetitions of 'value'
                decoded_values.extend([value] * count)
            else:
                # Handle case where there's no count (treat as single value)
                decoded_values.append(int(pair))
    
    # Reshape into matrix rows
    matrix = []
    for i in range(rows):
        start_idx = i * cols
        end_idx = start_idx + cols
        row = decoded_values[start_idx:end_idx]
        matrix.append(row)
    
    # Return as JSON string
    return json.dumps(matrix)