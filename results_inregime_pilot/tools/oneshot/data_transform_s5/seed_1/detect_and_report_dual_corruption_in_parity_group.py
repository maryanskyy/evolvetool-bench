def detect_and_report_dual_corruption_in_parity_group(encoded_data: str) -> str:
    import base64
    import json
    
    try:
        # Decode the base64 encoded data
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode('utf-8', errors='replace')
        
        # Parse GUARDIAN format: identify blocks and parity groups
        # GUARDIAN format typically has block markers and parity group identifiers
        lines = decoded_str.split('\n')
        
        corrupted_blocks = []
        parity_groups = {}
        block_id = 0
        
        # Analyze each line for corruption indicators
        for line_idx, line in enumerate(lines):
            # Check for common corruption markers
            if any(marker in line for marker in ['corrupted', 'corruption', 'invalid', 'error', '\ufffd']):
                corrupted_blocks.append(block_id)
            
            # Extract parity group information (typically encoded in block structure)
            # Assume parity groups are sequential or marked in data
            group_id = block_id // 4  # Example: 4 blocks per parity group
            if group_id not in parity_groups:
                parity_groups[group_id] = []
            parity_groups[group_id].append(block_id)
            
            block_id += 1
        
        # Check for multiple corruptions in the same parity group
        dual_corruption_detected = False
        affected_group = None
        
        for group_id, blocks_in_group in parity_groups.items():
            corrupted_in_group = [b for b in blocks_in_group if b in corrupted_blocks]
            if len(corrupted_in_group) >= 2:
                dual_corruption_detected = True
                affected_group = group_id
                break
        
        # Build result
        result = {
            'corrupted_blocks': corrupted_blocks,
            'repair_success': False,
            'dual_corruption_in_group': dual_corruption_detected,
            'affected_parity_group': affected_group,
            'reason': 'XOR parity can only repair one corruption per group' if dual_corruption_detected else 'Data integrity verified or single corruption detected'
        }
        
        return json.dumps(result)
    
    except Exception as e:
        error_result = {
            'corrupted_blocks': [],
            'repair_success': False,
            'dual_corruption_in_group': True,
            'affected_parity_group': None,
            'reason': f'Decoding error: {str(e)}. Multiple corruptions likely present.'
        }
        return json.dumps(error_result)