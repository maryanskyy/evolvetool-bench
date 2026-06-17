def decode_arcsig_and_compute_spectrum(arcsig_string):
    import base64
    import struct
    import json
    
    # Parse ARCSIG header
    parts = arcsig_string.split(';')
    metadata = {}
    base64_payload = None
    
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            metadata[key] = value
        elif part.startswith('ARCSIG:'):
            metadata['version'] = part.split(':')[1]
    
    # Extract parameters
    sample_rate = int(metadata['SR'])
    n_samples = int(metadata['LEN'])
    base64_payload = metadata['ENC'].split(';')[1] if ';' in metadata['ENC'] else None
    
    # Find base64 payload (everything after ENC:f32le_b64;)
    enc_index = arcsig_string.find('ENC:f32le_b64;')
    if enc_index != -1:
        base64_payload = arcsig_string[enc_index + len('ENC:f32le_b64;'):]
    
    # Decode base64
    decoded_bytes = base64.b64decode(base64_payload)
    
    # Unpack as little-endian float32 values
    samples = struct.unpack('<' + 'f' * (len(decoded_bytes) // 4), decoded_bytes)
    
    # Compute FFT
    import cmath
    N = len(samples)
    fft_result = [0] * N
    
    for k in range(N):
        for n in range(N):
            angle = -2j * cmath.pi * k * n / N
            fft_result[k] += samples[n] * cmath.exp(angle)
    
    # Compute one-sided spectrum
    spectrum = []
    for k in range(N // 2 + 1):
        freq_hz = round(k * sample_rate / N, 4)
        magnitude = round(abs(fft_result[k]) / N, 4)
        spectrum.append({"freq_hz": freq_hz, "magnitude": magnitude})
    
    return json.dumps(spectrum)