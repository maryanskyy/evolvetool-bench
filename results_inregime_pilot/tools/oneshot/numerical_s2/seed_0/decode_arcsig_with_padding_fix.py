def decode_arcsig_with_padding_fix(arcsig_signal: str) -> str:
    import base64
    import json
    import struct
    import math
    
    try:
        # Parse ARCSIG header
        parts = arcsig_signal.split(';')
        metadata = {}
        b64_data = None
        
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                if key == 'ENC':
                    metadata['encoding'] = value
                elif key == 'SR':
                    metadata['sample_rate'] = int(value)
                elif key == 'LEN':
                    metadata['length'] = int(value)
                elif key == 'v1':
                    pass
            else:
                # This is the base64 data part
                b64_data = part
        
        if not b64_data:
            return json.dumps({"error": "No base64 data found in ARCSIG signal"})
        
        # Fix base64 padding
        padding_needed = (4 - len(b64_data) % 4) % 4
        b64_data_padded = b64_data + '=' * padding_needed
        
        # Decode base64
        try:
            decoded_bytes = base64.b64decode(b64_data_padded)
        except Exception as e:
            return json.dumps({"error": f"Base64 decode failed: {str(e)}"})
        
        # Parse float32 little-endian data
        num_samples = len(decoded_bytes) // 4
        samples = []
        for i in range(num_samples):
            offset = i * 4
            value = struct.unpack('<f', decoded_bytes[offset:offset+4])[0]
            samples.append(value)
        
        # Compute FFT (simple DFT implementation)
        n = len(samples)
        spectrum = []
        
        for k in range(n // 2 + 1):
            real = 0.0
            imag = 0.0
            for n_idx in range(n):
                angle = -2.0 * math.pi * k * n_idx / n
                real += samples[n_idx] * math.cos(angle)
                imag += samples[n_idx] * math.sin(angle)
            
            magnitude = math.sqrt(real * real + imag * imag) / n
            freq_hz = k * metadata.get('sample_rate', 100) / n
            spectrum.append({"freq_hz": round(freq_hz, 2), "magnitude": round(magnitude, 6)})
        
        return json.dumps(spectrum)
    
    except Exception as e:
        return json.dumps({"error": f"Processing failed: {str(e)}"})