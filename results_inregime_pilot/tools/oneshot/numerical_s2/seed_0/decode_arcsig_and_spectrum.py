import json
import base64
import struct
from math import pi, sqrt

def decode_arcsig_and_spectrum(arcsig_string):
    """
    Decodes an ARCSIG signal and computes its frequency spectrum.
    
    Args:
        arcsig_string: ARCSIG format string with metadata and base64-encoded signal data
        
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
    
    # Find and decode base64 data (everything after last semicolon that's not a key:value pair)
    for part in parts:
        if ':' not in part and part:
            data_b64 = part
            break
    
    if not data_b64:
        return json.dumps([])
    
    # Decode base64
    try:
        data_bytes = base64.b64decode(data_b64)
    except:
        return json.dumps([])
    
    # Parse float32 little-endian data
    signal = []
    for i in range(0, len(data_bytes), 4):
        if i + 4 <= len(data_bytes):
            value = struct.unpack('<f', data_bytes[i:i+4])[0]
            signal.append(value)
    
    # Ensure we have the right length
    signal = signal[:length]
    
    if len(signal) == 0:
        return json.dumps([])
    
    # Compute FFT using DFT (Discrete Fourier Transform)
    n = len(signal)
    spectrum = []
    
    for k in range(n // 2 + 1):
        real = 0.0
        imag = 0.0
        
        for t in range(n):
            angle = -2.0 * pi * k * t / n
            real += signal[t] * (angle ** 0 if angle == 0 else __import__('math').cos(angle))
            imag += signal[t] * __import__('math').sin(angle)
        
        magnitude = sqrt(real * real + imag * imag) / n
        freq_hz = k * sample_rate / n
        spectrum.append({"freq_hz": round(freq_hz, 2), "magnitude": round(magnitude, 6)})
    
    return json.dumps(spectrum)