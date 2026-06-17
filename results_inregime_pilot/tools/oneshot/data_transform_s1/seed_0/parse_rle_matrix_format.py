def parse_rle_matrix_format(rle_string: str) -> str:
    """
    Parses RLE matrix format: rows separated by ';', each row has value:count pairs separated by ':'
    Example: '2,6;5:2,0:7,5:3' means 2 rows of 6 columns, row1 has 5 twice then 0 seven times, row2 has 5 three times
    """
    parts = rle_string.split(';')
    
    # Parse dimensions from first part
    dims = parts[0].split(',')
    num_rows = int(dims[0])
    num_cols = int(dims[1])
    
    # Parse the encoded rows
    result = []
    row_index = 0
    
    for i in range(1, len(parts)):
        if row_index >= num_rows:
            break
            
        row_data = parts[i].split(',')
        current_row = []
        
        j = 0
        while j < len(row_data) and len(current_row) < num_cols:
            # Each pair is value:count
            if ':' in row_data[j]:
                value, count = row_data[j].split(':')
                value = int(value)
                count = int(count)
                current_row.extend([value] * count)
            j += 1
        
        # Handle case where value:count spans across comma boundaries
        if len(current_row) < num_cols and j < len(row_data):
            # Merge remaining parts to find complete value:count pairs
            remaining = ','.join(row_data[j:])
            pairs = remaining.split(',')
            for pair in pairs:
                if ':' in pair and len(current_row) < num_cols:
                    value, count = pair.split(':')
                    value = int(value)
                    count = int(count)
                    current_row.extend([value] * count)
        
        result.append(current_row[:num_cols])
        row_index += 1
    
    return str(result)