def parse_rle_matrix(rle_string):
    """
    Parse a Run-Length Encoded (RLE) matrix string into a list of lists.
    
    Utility:
        Decodes a compact RLE format representing a 2D matrix where each row
        is separated by semicolons and each value is encoded as "count:value"
        pairs separated by commas.
    
    Args:
        rle_string (str): RLE encoded matrix string in format "count:value,count:value;..."
                         Example: "2,6;5:2,0:7,5:3" represents a 2x6 matrix
    
    Returns:
        list of lists: 2D matrix where each inner list represents a row
    
    """
    rows = []
    
    # Split by semicolon to get individual rows
    row_strings = rle_string.split(';')
    
    for row_string in row_strings:
        row = []
        
        # Split by comma to get individual count:value pairs
        pairs = row_string.split(',')
        
        for pair in pairs:
            # Handle both "count:value" and single "value" formats
            if ':' in pair:
                count, value = pair.split(':')
                count = int(count)
                value = int(value)
            else:
                # If no colon, treat as single value with count of 1
                count = 1
                value = int(pair)
            
            # Expand the value by count and add to row
            row.extend([value] * count)
        
        rows.append(row)
    
    return rows