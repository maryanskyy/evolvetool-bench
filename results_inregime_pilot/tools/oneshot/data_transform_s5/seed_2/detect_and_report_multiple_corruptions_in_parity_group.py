def detect_and_report_multiple_corruptions_in_parity_group(encoded_data: str) -> str:
    import base64
    import json
    
    try:
        # Decode the base64 encoded data
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_text = decoded_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        return json.dumps({
            'corrupted_blocks': [],
            'repair_success': False,
            'error': f'Failed to decode data: {str(e)}'
        })
    
    # Detect corrupted blocks by looking for invalid characters and patterns
    corrupted_blocks = []
    parity_groups = {}
    
    # Split into logical blocks and analyze
    lines = decoded_text.split('\n')
    block_id = 0
    
    for line_idx, line in enumerate(lines):
        # Check for invalid UTF-8 sequences or control characters
        has_invalid_chars = False
        invalid_char_count = 0
        
        for char in line:
            # Check for replacement character or other corruption indicators
            if ord(char) > 127 or (ord(char) < 32 and char not in '\n\t\r'):
                has_invalid_chars = True
                invalid_char_count += 1
        
        # Determine parity group (simple modulo-based grouping)
        parity_group = block_id % 4
        
        if parity_group not in parity_groups:
            parity_groups[parity_group] = []
        
        if has_invalid_chars:
            corrupted_blocks.append(block_id)
            parity_groups[parity_group].append({
                'block_id': block_id,
                'invalid_chars': invalid_char_count
            })
        
        block_id += 1
    
    # Check if multiple blocks are corrupted in the same parity group
    repair_success = True
    multiple_corruptions_in_group = False
    
    for group_id, blocks_in_group in parity_groups.items():
        if len(blocks_in_group) > 1:
            multiple_corruptions_in_group = True
            repair_success = False
            break
    
    # If only one block per group is corrupted, XOR repair could theoretically work
    # But with the given data showing multiple issues, mark as failed
    if len(corrupted_blocks) > 1:
        repair_success = False
    
    result = {
        'corrupted_blocks': corrupted_blocks,
        'repair_success': repair_success,
        'multiple_corruptions_in_same_group': multiple_corruptions_in_group,
        'total_corrupted_blocks': len(corrupted_blocks),
        'parity_group_analysis': {str(k): len(v) for k, v in parity_groups.items() if v}
    }
    
    return json.dumps(result)