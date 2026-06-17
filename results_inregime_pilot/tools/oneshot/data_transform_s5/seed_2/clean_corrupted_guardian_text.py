def clean_corrupted_guardian_text(encoded_data: str) -> str:
    import base64
    import re
    
    # Decode base64
    try:
        decoded = base64.b64decode(encoded_data).decode('utf-8', errors='replace')
    except Exception:
        return '{"text": "", "was_corrupted": false, "blocks_repaired": 0}'
    
    # Parse GUARDIAN format: blocks are separated by markers
    # Format appears to be: [block_id][size][data]
    blocks = []
    corrupted_indices = []
    text_parts = []
    
    # Extract readable text and identify corruption patterns
    # Corrupted blocks contain non-ASCII or control characters
    current_block = ""
    block_id = 0
    is_corrupted = False
    blocks_repaired = 0
    
    for i, char in enumerate(decoded):
        # Detect corruption: non-printable chars, invalid UTF-8 sequences
        if ord(char) < 32 and char not in '\n\t\r':
            is_corrupted = True
            corrupted_indices.append(block_id)
        elif ord(char) > 126 and ord(char) < 160:
            is_corrupted = True
            corrupted_indices.append(block_id)
        
        if char in '\x00' or (ord(char) > 127 and ord(char) < 160):
            if current_block:
                blocks.append((block_id, current_block, is_corrupted))
                if is_corrupted:
                    blocks_repaired += 1
                current_block = ""
                block_id += 1
                is_corrupted = False
        else:
            current_block += char
    
    if current_block:
        blocks.append((block_id, current_block, is_corrupted))
        if is_corrupted:
            blocks_repaired += 1
    
    # Repair corrupted blocks by removing non-printable characters
    repaired_text = ""
    for block_id, text, corrupted in blocks:
        if corrupted:
            # Remove non-printable characters and reconstruct
            cleaned = ''.join(c for c in text if ord(c) >= 32 or c in '\n\t\r')
            repaired_text += cleaned
        else:
            repaired_text += text
    
    # Clean up extra spaces and artifacts
    repaired_text = re.sub(r'\s+', ' ', repaired_text).strip()
    
    # Build result
    was_corrupted = len(corrupted_indices) > 0
    result = {
        'text': repaired_text,
        'was_corrupted': was_corrupted,
        'blocks_repaired': blocks_repaired
    }
    
    import json
    return json.dumps(result)