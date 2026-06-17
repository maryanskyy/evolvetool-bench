def parse_rle_matrix(rle_string):
    """
    Parse a Run-Length Encoded (RLE) matrix string into a list of lists.

    Utility:
        Decodes a compact RLE format representing a 2D matrix where consecutive
        identical values are represented as count:value pairs. Rows are separated
        by semicolons, and count:value pairs within a row are separated by commas.

    Args:
        rle_string (str): RLE encoded matrix in format "count:value,count:value;..."
                         Example: "2:6;5:2,0:7,5:3" represents a matrix

    Returns:
        list of lists: 2D matrix where each inner list represents a row
                      Example: [[6, 6], [2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5]]
    """
    matrix = []
    rows = rle_string.split(';')

    for row_data in rows:
        row = []
        pairs = row_data.split(',')

        for pair in pairs:
            # Each pair is in format "count:value"
            parts = pair.split(':')
            if len(parts) == 2:
                count = int(parts[0])
                value = int(parts[1])
                row.extend([value] * count)

        matrix.append(row)

    return matrix