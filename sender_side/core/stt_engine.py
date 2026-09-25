"""
Offline STT Engine Module
Wraps Sherpa-ONNX for INT8 Quantized Zipformer inference. Optimized for sub-150MB RAM.
"""
import sherpa_onnx
import time

class STTEngine:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        print("[STT] Loading INT8 Zipformer Model...")
        try:
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder="assets/stt/encoder-epoch-99-avg-1.onnx",
                decoder="assets/stt/decoder-epoch-99-avg-1.onnx",
                joiner="assets/stt/joiner-epoch-99-avg-1.onnx",
                tokens="assets/stt/tokens.txt",
                num_threads=1, # Restrict threads to save memory and CPU on edge
                sample_rate=self.sample_rate,
                feature_dim=80,
                decoding_method="greedy_search"
            )
            print("[STT] Model loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load STT model: {e}")
            raise

    def transcribe(self, audio_array) -> str:
        """Transcribes a full sentence audio array to UTF-8 text."""
        start_time = time.time()
        
        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.sample_rate, audio_array)
        self.recognizer.decode_stream(stream)
        
        text = stream.result.text.strip()
        latency = time.time() - start_time
        
        # Explicit memory cleanup to maintain sub-150MB footprint
        del stream
        del audio_array
        
        if text:
            print(f"[STT] Transcribed in {latency:.2f}s: '{text}'")
        return text