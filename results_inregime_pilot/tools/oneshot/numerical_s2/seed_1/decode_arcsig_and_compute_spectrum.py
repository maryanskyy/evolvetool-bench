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
            if key == 'SR':
                metadata['sample_rate'] = int(value)
            elif key == 'LEN':
                metadata['n_samples'] = int(value)
            elif key == 'ENC':
                metadata['encoding'] = value
        elif part.startswith('ARCSIG:'):
            continue
        else:
            # This is the base64 payload (everything after the last semicolon)
            base64_payload = part
    
    # Decode base64
    decoded_bytes = base64.b64decode(base64_payload)
    
    # Unpack as little-endian float32 values
    n_samples = metadata['n_samples']
    samples = struct.unpack('<' + 'f' * n_samples, decoded_bytes)
    
    # Compute FFT
    import math
    
    # Simple FFT implementation using Cooley-Tukey algorithm
    def fft(x):
        N = len(x)
        if N <= 1:
            return x
        even = fft([x[i] for i in range(0, N, 2)])
        odd = fft([x[i] for i in range(1, N, 2)])
        T = [complex(math.cos(-2.0 * math.pi * k / N), math.sin(-2.0 * math.pi * k / N)) * odd[k] for k in range(N // 2)]
        return [even[k] + T[k] for k in range(N // 2)] + [even[k] - T[k] for k in range(N // 2)]
    
    fft_result = fft(list(samples))
    
    # Compute one-sided spectrum
    sample_rate = metadata['sample_rate']
    N = n_samples
    spectrum = []
    
    for k in range(N // 2 + 1):
        freq_hz = round(k * sample_rate / N, 4)
        magnitude = round(abs(fft_result[k]) / N, 4)
        spectrum.append({"freq_hz": freq_hz, "magnitude": magnitude})
    
    return json.dumps(spectrum)