def parse_rle_matrix_format(rle_string: str) -> str:
    """
    Parses RLE matrix format: rows are separated by semicolons,
    each row contains value:count pairs separated by commas.
    Format: value,count;value:count;value:count etc.
    Returns a string representation of the list of lists.
    """
    result = []
    
    # Split by semicolon to get rows
    rows = rle_string.split(';')
    
    for row_str in rows:
        row = []
        # Split by comma to get value:count pairs
        pairs = row_str.split(',')
        
        for pair in pairs:
            # Handle both 'value:count' and 'value' formats
            if ':' in pair:
                parts = pair.split(':')
                value = int(parts[0])
                count = int(parts[1])
            else:
                # If no colon, treat as single value with count 1
                value = int(pair)
                count = 1
            
            # Add the value 'count' times to the row
            row.extend([value] * count)
        
        result.append(row)
    
    return str(result)