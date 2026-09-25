"""
Continuous Mic Capture Module
Captures 16 kHz mono PCM audio into a thread-safe, non-blocking queue.
"""
import queue
import sys
import numpy as np
import sounddevice as sd

class MicStream:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = 1
        self.audio_queue = queue.Queue()
        self.stream = None

    def _callback(self, indata, frames, time, status):
        """High-priority audio callback pushing raw PCM frames to the queue."""
        if status:
            print(f"[AUDIO WARNING] {status}", file=sys.stderr)
        # Flatten and cast to float32 for ONNX compatibility
        self.audio_queue.put(indata.flatten().astype(np.float32))

    def start(self):
        """Initializes and starts the non-blocking audio stream."""
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=self._callback
            )
            self.stream.start()
            print(f"[MIC] Started capture at {self.sample_rate}Hz, Mono.")
        except Exception as e:
            print(f"[ERROR] Failed to open audio stream: {e}", file=sys.stderr)
            sys.exit(1)

    def stop(self):
        """Stops and closes the audio stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            print("[MIC] Audio stream stopped.")