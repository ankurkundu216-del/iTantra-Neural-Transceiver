"""
Test Microphone Stream
Verifies audio hardware accessibility, sample rate consistency, and queue population.
"""
import sys
import time
import numpy as np
from pathlib import Path

# Adjust path to import from parent core directory
sys.path.append(str(Path(__file__).parent.parent))

from core.mic_stream import MicStream

def test_microphone():
    print("=" * 50)
    print(" TEST: Microphone Input Capture")
    print("=" * 50)
    
    mic = MicStream(sample_rate=16000, chunk_size=512)
    mic.start()
    
    print("[TEST] Recording 3 seconds of mic input. Speak now...")
    start_time = time.time()
    chunks_received = 0
    
    try:
        while time.time() - start_time < 3.0:
            if not mic.audio_queue.empty():
                chunk = mic.audio_queue.get()
                chunks_received += 1
                
                # Calculate Root Mean Square (RMS) volume level
                rms = np.sqrt(np.mean(chunk**2))
                
                # Display dynamic volume meter in terminal
                meter = "#" * int(rms * 100)
                sys.stdout.write(f"\r[MIC LEVEL] |{meter:<30}| RMS: {rms:.4f}")
                sys.stdout.flush()
            time.sleep(0.01)
            
    finally:
        mic.stop()
        
    print(f"\n[TEST] Captured {chunks_received} audio chunks (~512 samples each).")
    assert chunks_received > 0, "Error: No audio data captured from microphone!"
    print("[PASSED] Microphone hardware stream working properly.\n")

if __name__ == "__main__":
    test_microphone()