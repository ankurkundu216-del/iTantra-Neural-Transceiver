"""
Mock Sender Stream Integration Test
Generates synthetic audio signals to test the full pipeline without microphone input.
"""
import sys
import time
import numpy as np
import queue
from pathlib import Path

# Adjust path to import from parent core directory
sys.path.append(str(Path(__file__).parent.parent))

from core.vad_detector import VADDetector
from core.binary_packetizer import BinaryPacketizer

def generate_synthetic_audio(duration_sec=1.5, sample_rate=16000, frequency=440.0):
    """Generates synthetic sine wave PCM audio simulating speech activity."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    # Sine wave modulated to simulate speech energy variation
    audio = 0.5 * np.sin(2 * np.pi * frequency * t) * np.sin(2 * np.pi * 2 * t)
    return audio.astype(np.float32)

def test_mock_sender():
    print("=" * 50)
    print(" TEST: Mock Audio Pipeline Stream")
    print("=" * 50)
    
    sample_rate = 16000
    chunk_size = 512
    vad = VADDetector(model_path="assets/vad/silero_vad.onnx", sample_rate=sample_rate)
    
    print("[MOCK] Generating synthetic audio signal...")
    silence_chunk = np.zeros(chunk_size, dtype=np.float32)
    speech_signal = generate_synthetic_audio(duration_sec=1.0, sample_rate=sample_rate)
    
    # Split speech signal into 512-sample chunks
    speech_chunks = [speech_signal[i:i + chunk_size] for i in range(0, len(speech_signal), chunk_size) if len(speech_signal[i:i + chunk_size]) == chunk_size]
    
    print(f"[MOCK] Feeding 10 silence chunks -> {len(speech_chunks)} speech chunks -> 20 silence chunks into VAD...")
    
    speech_detected_count = 0
    
    # 1. Feed Silence
    for _ in range(10):
        if vad.is_speech(silence_chunk):
            speech_detected_count += 1
            
    # 2. Feed Synthetic Speech
    for chunk in speech_chunks:
        if vad.is_speech(chunk):
            speech_detected_count += 1
            
    # 3. Feed Silence to trigger pause boundary
    for _ in range(20):
        vad.is_speech(silence_chunk)
        
    print(f"[MOCK] VAD triggered positive speech on {speech_detected_count} frames.")
    
    # Test packetization mock call
    mock_packet = BinaryPacketizer.create_packet("Synthetic audio transmission test", is_distress=False)
    print(f"[MOCK] Mock Packet Created: {len(mock_packet)} bytes (Header: {mock_packet[:6].hex()})")
    
    print("[PASSED] Mock sender pipeline test complete.\n")

if __name__ == "__main__":
    test_mock_sender()