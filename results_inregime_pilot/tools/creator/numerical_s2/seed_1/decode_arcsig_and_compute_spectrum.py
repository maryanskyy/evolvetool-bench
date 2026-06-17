def decode_arcsig_and_compute_spectrum(signal_string):
    """
    Decode an ARCSIG signal and compute its frequency spectrum.
    
    Utility:
        Parses ARCSIG format signals, decodes the base64-encoded float data,
        and computes the frequency spectrum using FFT.
    
    Args:
        signal_string (str): ARCSIG formatted signal string containing metadata
                            and base64-encoded sample data
    
    Returns:
        list: List of dicts with keys "freq_hz" and "magnitude" representing
              the frequency spectrum
    """
    import base64
    import struct
    
    # Parse ARCSIG header
    parts = signal_string.split(';')
    metadata = {}
    data_b64 = None
    
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            if key == 'ENC':
                data_b64 = value
            else:
                metadata[key] = value
    
    # Extract metadata
    sample_rate = int(metadata.get('SR', 100))
    length = int(metadata.get('LEN', 128))
    encoding = metadata.get('ENC', 'f32le_b64')
    
    # Find the actual base64 data (everything after the last semicolon with data)
    signal_parts = signal_string.split(';')
    data_b64 = signal_parts[-1]
    
    # Decode base64
    try:
        decoded_bytes = base64.b64decode(data_b64)
    except Exception as e:
        # Try with padding
        padding = 4 - (len(data_b64) % 4)
        if padding != 4:
            data_b64 += '=' * padding
        decoded_bytes = base64.b64decode(data_b64)
    
    # Parse float32 little-endian data
    num_samples = len(decoded_bytes) // 4
    samples = struct.unpack(f'<{num_samples}f', decoded_bytes)
    
    # Compute FFT
    import cmath
    
    n = len(samples)
    if n == 0:
        return []
    
    # Simple FFT implementation (Cooley-Tukey)
    def fft(x):
        n = len(x)
        if n <= 1:
            return x
        even = fft([x[i] for i in range(0, n, 2)])
        odd = fft([x[i] for i in range(1, n, 2)])
        t = [cmath.exp(-2j * cmath.pi * k / n) * odd[k] for k in range(n // 2)]
        return [even[k] + t[k] for k in range(n // 2)] + [even[k] - t[k] for k in range(n // 2)]
    
    # Pad to power of 2
    padded_len = 1
    while padded_len < n:
        padded_len *= 2
    padded_samples = list(samples) + [0] * (padded_len - n)
    
    # Compute FFT
    fft_result = fft(padded_samples)
    
    # Compute magnitude spectrum
    spectrum = []
    for k in range(len(fft_result) // 2):
        freq = k * sample_rate / len(fft_result)
        magnitude = abs(fft_result[k]) / len(fft_result)
        spectrum.append({"freq_hz": round(freq, 2), "magnitude": round(magnitude, 6)})
    
    return spectrum