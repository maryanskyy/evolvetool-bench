def parse_rle_matrix(rle_string):
    """
    Parse a Run-Length Encoded (RLE) matrix string into a list of lists.

    Utility:
        Decodes a compact RLE format representing a 2D matrix where values and their
        run lengths are specified. Format: "value,count;value:count;..." where semicolons
        separate rows and colons separate value-count pairs within rows.

    Args:
        rle_string (str): RLE encoded matrix string in format "value,count;value:count;..."
                         Example: "2,6;5:2,0:7,5:3"

    Returns:
        list of lists: 2D matrix where each inner list represents a row with decoded values
                      Example: [[2, 2, 2, 2, 2, 2], [5, 5, 0, 0, 0, 0, 0, 5, 5, 5]]
    """
    matrix = []
    rows = rle_string.split(';')

    for row_str in rows:
        row = []
        # Split by colon to get value:count pairs
        pairs = row_str.split(':')

        for pair in pairs:
            # Each pair is in format "value,count"
            if ',' in pair:
                parts = pair.split(',')
                value = int(parts[0])
                count = int(parts[1])
            else:
                # If no comma, it's just a value with count 1
                value = int(pair)
                count = 1

            row.extend([value] * count)

        matrix.append(row)

    return matrix