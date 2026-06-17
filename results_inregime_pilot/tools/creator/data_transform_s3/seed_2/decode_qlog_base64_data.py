def decode_qlog_base64_data(encoded_data: str) -> dict:
    """
    Decode QLOG data from base64 format and extract log records.
    
    Utility:
        Decodes base64-encoded QLOG data and attempts to parse it into structured
        log records. Handles both binary QLOG format and plain text messages.
        Returns parsed records with metadata about the decoding process.
    
    Args:
        encoded_data (str): Base64-encoded QLOG data string
    
    Returns:
        dict: A dictionary containing:
            - 'raw_decoded': The raw decoded bytes as string
            - 'text_content': Extracted text content if present
            - 'records': List of parsed log records (dict format)
            - 'format_type': Identified format type ('text', 'binary', or 'unknown')
            - 'success': Boolean indicating successful parsing
    """
    import base64
    import struct
    
    result = {
        'raw_decoded': None,
        'text_content': None,
        'records': [],
        'format_type': 'unknown',
        'success': False
    }
    
    try:
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        result['raw_decoded'] = decoded_bytes.hex()
        
        # Try to extract text content
        try:
            text_content = decoded_bytes.decode('utf-8', errors='ignore')
            result['text_content'] = text_content.strip()
            
            # Check if it contains readable text
            if len(text_content.strip()) > 0 and any(c.isalpha() for c in text_content):
                result['format_type'] = 'text'
                # Parse as simple text log record
                result['records'] = [{
                    'type': 'text_message',
                    'content': text_content.strip(),
                    'length': len(decoded_bytes)
                }]
                result['success'] = True
                return result
        except Exception:
            pass
        
        # Try to parse as binary QLOG format
        if len(decoded_bytes) >= 4:
            result['format_type'] = 'binary'
            try:
                # Attempt to extract header information
                header_values = struct.unpack('>I', decoded_bytes[:4])
                record = {
                    'type': 'binary_record',
                    'header': header_values[0],
                    'data_length': len(decoded_bytes),
                    'hex_data': decoded_bytes.hex()
                }
                result['records'] = [record]
                result['success'] = True
                return result
            except struct.error:
                pass
        
        # If no specific format matched, return raw data as record
        result['format_type'] = 'unknown'
        result['records'] = [{
            'type': 'raw_data',
            'hex': decoded_bytes.hex(),
            'length': len(decoded_bytes)
        }]
        result['success'] = True
        
    except base64.binascii.Error as e:
        result['error'] = f"Base64 decoding error: {str(e)}"
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
    
    return result


# Test with the provided data
if __name__ == "__main__":
    test_data = "APM8wDcAABhEaXNrIHVzYWdlIGF0IDg1IHBlcmNlbnQ="
    result = decode_qlog_base64_data(test_data)
    print(result)