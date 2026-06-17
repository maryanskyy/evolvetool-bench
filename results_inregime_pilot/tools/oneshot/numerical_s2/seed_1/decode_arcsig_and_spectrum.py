import json
import base64
import struct
from math import sqrt

def decode_arcsig_and_spectrum(arcsig_string):
    """
    Decodes an ARCSIG signal and computes its frequency spectrum.
    
    Args:
        arcsig_string: ARCSIG format string with metadata and base64-encoded signal
        
    Returns:
        JSON string containing list of {"freq_hz": ..., "magnitude": ...} objects
    """
    # Parse ARCSIG header
    parts = arcsig_string.split(';')
    metadata = {}
    data_b64 = None
    
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            metadata[key] = value
    
    # Extract parameters
    sample_rate = int(metadata.get('SR', '100'))
    length = int(metadata.get('LEN', '128'))
    encoding = metadata.get('ENC', 'f32le_b64')
    
    # Find and decode base64 data (last part after last semicolon)
    data_b64 = parts[-1]
    
    # Decode base64
    try:
        binary_data = base64.b64decode(data_b64)
    except:
        return json.dumps([])
    
    # Parse binary data based on encoding
    signal = []
    if 'f32le' in encoding:
        # 32-bit little-endian floats
        for i in range(0, len(binary_data), 4):
            if i + 4 <= len(binary_data):
                value = struct.unpack('<f', binary_data[i:i+4])[0]
                signal.append(value)
    
    # Ensure we have the right length
    signal = signal[:length]
    
    if len(signal) == 0:
        return json.dumps([])
    
    # Simple FFT implementation (Cooley-Tukey)
    def fft(x):
        N = len(x)
        if N <= 1:
            return x
        
        even = fft([x[i] for i in range(0, N, 2)])
        odd = fft([x[i] for i in range(1, N, 2)])
        
        T = []
        for k in range(N // 2):
            w = complex(0, -2.0 * 3.141592653589793 * k / N)
            import cmath
            t = cmath.exp(w) * odd[k]
            T.append(t)
        
        return [even[k] + T[k] for k in range(N // 2)] + [even[k] - T[k] for k in range(N // 2)]
    
    # Convert to complex for FFT
    complex_signal = [complex(x, 0) for x in signal]
    
    # Compute FFT
    spectrum = fft(complex_signal)
    
    # Compute magnitudes and frequencies
    result = []
    nyquist_freq = sample_rate / 2.0
    freq_resolution = sample_rate / float(len(signal))
    
    for k in range(len(spectrum) // 2):
        freq_hz = k * freq_resolution
        magnitude = abs(spectrum[k]) / len(signal)
        result.append({"freq_hz": round(freq_hz, 2), "magnitude": round(magnitude, 6)})
    
    return json.dumps(result)