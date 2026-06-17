def apply_bandpass_filter_to_arcsig(arcsig_signal: str, filter_spec: str) -> str:
    """
    Apply a band-pass filter to an ARCSIG signal.

    Utility:
        Filters an ARCSIG-encoded signal using FFT-based band-pass filtering.
        Zeros out frequency components outside the specified band and returns
        the filtered signal as a new ARCSIG string.

    Args:
        arcsig_signal: ARCSIG-encoded signal string (format: ARCSIG:v1;SR:...;LEN:...;ENC:...;DATA)
        filter_spec: Filter specification string (format: BANDPASS:<low_hz>,<high_hz>)

    Returns:
        Filtered ARCSIG signal string with same SR, LEN, and ENC format
    """

    # Parse ARCSIG header
    # Format: ARCSIG:v1;SR:100;LEN:128;ENC:f32le_b64;DATA
    parts = arcsig_signal.split(';')
    header = {}
    data_b64 = None

    for i, part in enumerate(parts):
        if '=' in part:
            key, value = part.split('=', 1)
            header[key] = value
        elif ':' in part:
            key, value = part.split(':', 1)
            header[key] = value

    # The data part is everything after the last semicolon
    # Find where the data starts (after ENC:f32le_b64;)
    arcsig_prefix = "ARCSIG:v1;SR:"
    prefix_end = arcsig_signal.find(';ENC:')
    if prefix_end != -1:
        enc_end = arcsig_signal.find(';', prefix_end + 1)
        if enc_end != -1:
            data_b64 = arcsig_signal[enc_end + 1:]

    sr = int(header['SR'])
    length = int(header['LEN'])
    enc = header['ENC']

    # Parse filter spec
    filter_parts = filter_spec.split(':')
    low_hz = float(filter_parts[1].split(',')[0])
    high_hz = float(filter_parts[1].split(',')[1])

    # Decode base64 data
    data_bytes = base64.b64decode(data_b64)

    # Unpack float32 samples (little-endian)
    samples = struct.unpack(f'<{length}f', data_bytes)
    samples = np.array(samples, dtype=np.float32)

    # Compute FFT
    fft_result = np.fft.fft(samples)

    # Create frequency array
    freqs = np.fft.fftfreq(length, 1.0 / sr)

    # Zero out bins outside [low_hz, high_hz]
    # For real signals, we need to handle both positive and negative frequencies
    # Keep only frequencies strictly within [low_hz, high_hz]
    mask = (np.abs(freqs) < low_hz) | (np.abs(freqs) > high_hz)
    fft_result[mask] = 0.0

    # Compute IFFT and take real part
    filtered_samples = np.fft.ifft(fft_result).real

    # Re-encode as ARCSIG
    data_bytes = struct.pack(f'<{length}f', *filtered_samples)
    data_b64_new = base64.b64encode(data_bytes).decode('ascii')

    # Reconstruct ARCSIG string
    result = f"ARCSIG:v1;SR:{sr};LEN:{length};ENC:{enc};{data_b64_new}"
    return result