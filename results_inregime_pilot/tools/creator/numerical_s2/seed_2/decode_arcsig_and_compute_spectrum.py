def decode_arcsig_and_compute_spectrum(signal_string):
    """
    Decode an ARCSIG signal and compute its frequency spectrum.
    
    Utility:
        Parses ARCSIG format signals, decodes the base64-encoded float data,
        and computes the frequency spectrum using FFT analysis.
    
    Args:
        signal_string (str): ARCSIG formatted signal string containing metadata
                            and base64-encoded sample data
    
    Returns:
        list: JSON-compatible list of dicts with keys "freq_hz" and "magnitude"
              representing the frequency spectrum
    """
    import base64
    import struct
    import math
    
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
    
    # Find the actual base64 data (everything after the last semicolon with actual data)
    signal_parts = signal_string.split(';')
    data_b64 = signal_parts[-1]
    
    # Decode base64
    try:
        decoded_bytes = base64.b64decode(data_b64)
    except Exception:
        # Try with padding
        padding = 4 - (len(data_b64) % 4)
        if padding != 4:
            data_b64 += '=' * padding
        decoded_bytes = base64.b64decode(data_b64)
    
    # Parse float32 little-endian samples
    samples = []
    for i in range(0, len(decoded_bytes), 4):
        if i + 4 <= len(decoded_bytes):
            value = struct.unpack('<f', decoded_bytes[i:i+4])[0]
            samples.append(value)
    
    # Compute FFT manually using Cooley-Tukey algorithm
    def fft(x):
        n = len(x)
        if n <= 1:
            return x
        even = fft([x[i] for i in range(0, n, 2)])
        odd = fft([x[i] for i in range(1, n, 2)])
        t = [math.e**(-2j * math.pi * k / n) * odd[k] for k in range(n // 2)]
        return [even[k] + t[k] for k in range(n // 2)] + [even[k] - t[k] for k in range(n // 2)]
    
    # Convert samples to complex numbers for FFT
    complex_samples = [complex(s, 0) for s in samples]
    
    # Compute FFT
    fft_result = fft(complex_samples)
    
    # Compute magnitude spectrum
    spectrum = []
    nyquist = sample_rate / 2
    freq_resolution = sample_rate / len(samples)
    
    for k in range(len(fft_result) // 2):
        freq = k * freq_resolution
        magnitude = abs(fft_result[k]) / len(samples)
        spectrum.append({
            "freq_hz": round(freq, 2),
            "magnitude": round(magnitude, 6)
        })
    
    return spectrum