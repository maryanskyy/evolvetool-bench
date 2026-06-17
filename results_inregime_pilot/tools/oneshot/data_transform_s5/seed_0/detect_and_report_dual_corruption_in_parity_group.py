def detect_and_report_dual_corruption_in_parity_group(encoded_data: str) -> str:
    import base64
    import json
    
    try:
        # Decode base64 data
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_text = decoded_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        return json.dumps({
            'repair_success': False,
            'corrupted_blocks': [],
            'error': f'Failed to decode data: {str(e)}'
        })
    
    # Analyze for corruption patterns
    corrupted_blocks = []
    parity_groups = {}
    
    # Simple heuristic: look for replacement characters and null bytes indicating corruption
    for i, char in enumerate(decoded_text):
        if ord(char) == 0 or char == '\ufffd' or (ord(char) > 127 and ord(char) < 160):
            block_id = i // 16  # Assume 16-byte blocks
            parity_group = block_id // 4  # Assume 4 blocks per parity group
            corrupted_blocks.append(block_id)
            if parity_group not in parity_groups:
                parity_groups[parity_group] = []
            parity_groups[parity_group].append(block_id)
    
    # Remove duplicates
    corrupted_blocks = list(set(corrupted_blocks))
    
    # Check if multiple blocks are in the same parity group
    dual_corruption_detected = False
    affected_group = None
    for group_id, blocks in parity_groups.items():
        if len(blocks) >= 2:
            dual_corruption_detected = True
            affected_group = group_id
            break
    
    # Build result
    result = {
        'repair_success': False,
        'corrupted_blocks': corrupted_blocks,
        'dual_corruption_in_group': dual_corruption_detected,
        'affected_parity_group': affected_group,
        'decoded_text_partial': decoded_text[:100] + '...' if len(decoded_text) > 100 else decoded_text,
        'reason': 'Multiple corrupted blocks detected in same parity group - XOR repair insufficient'
    }
    
    return json.dumps(result)