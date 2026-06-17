def decode_arcsig_and_compute_spectrum(signal_string):
    """
    Decode an ARCSIG signal and compute its frequency spectrum using FFT.

    Utility:
        Parses ARCSIG format signals (metadata + base64-encoded binary data),
        decodes the signal samples, and computes the magnitude spectrum using
        Fast Fourier Transform.

    Args:
        signal_string (str): ARCSIG formatted signal string containing metadata
                            (SR: sample rate, LEN: length, ENC: encoding) and
                            base64-encoded binary data.

    Returns:
        list: List of dictionaries with keys "freq_hz" and "magnitude",
              representing the frequency spectrum of the signal.
    """
    
    # Parse ARCSIG format
    parts = signal_string.split(';')
    metadata = {}
    data_b64 = None

    for i, part in enumerate(parts):
        if ':' in part:
            key, value = part.split(':', 1)
            if key == 'ENC':
                metadata[key] = value
            else:
                metadata[key] = value
        else:
            # The remaining parts after metadata are the base64 data
            if i > 0:
                data_b64 = part

    # Extract metadata
    sample_rate = int(metadata.get('SR', 100))
    length = int(metadata.get('LEN', 128))
    encoding = metadata.get('ENC', 'f32le_b64').split('_')[0]

    # Decode base64 data
    binary_data = base64.b64decode(data_b64)

    # Parse binary data based on encoding
    if encoding == 'f32le':
        # Little-endian 32-bit floats
        num_samples = len(binary_data) // 4
        samples = struct.unpack(f'<{num_samples}f', binary_data[:num_samples * 4])
    else:
        raise ValueError(f"Unsupported encoding: {encoding}")

    # Compute FFT using Cooley-Tukey algorithm
    def fft(x):
        n = len(x)
        if n <= 1:
            return x
        even = fft([x[i] for i in range(0, n, 2)])
        odd = fft([x[i] for i in range(1, n, 2)])
        t = [cmath.exp(-2j * cmath.pi * k / n) * odd[k] for k in range(n // 2)]
        return [even[k] + t[k] for k in range(n // 2)] + \
               [even[k] - t[k] for k in range(n // 2)]

    n = len(samples)
    if n == 0:
        return []

    fft_result = fft(list(samples))

    # Compute magnitude spectrum
    spectrum = []
    freq_resolution = sample_rate / n

    for k in range(n // 2 + 1):
        freq = k * freq_resolution
        magnitude = abs(fft_result[k]) / n
        spectrum.append({
            "freq_hz": round(freq, 4),
            "magnitude": round(magnitude, 4)
        })

    return spectrum