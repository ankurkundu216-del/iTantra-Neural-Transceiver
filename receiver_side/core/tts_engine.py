"""
Offline TTS Engine
Synthesizes UTF-8 text into float32 PCM audio using Sherpa-ONNX (MMS-VITS / Piper).
"""

import os
import time
from pathlib import Path
from typing import Tuple, Optional
import numpy as np

try:
    import sherpa_onnx
    SHERPA_TTS_AVAILABLE = True
except ImportError:
    SHERPA_TTS_AVAILABLE = False


class TTSEngine:
    def __init__(self, model_dir: Optional[str] = None, num_threads: int = 2):
        """
        Initializes the Sherpa-ONNX Offline TTS model.
        """
        self.num_threads = num_threads
        self.tts = None
        
        if model_dir is None:
            base_dir = Path(__file__).parent.parent
            model_dir = str(base_dir / "assets" / "tts")

        self.model_dir = model_dir
        self._initialize_engine()

    def _initialize_engine(self) -> None:
        if not SHERPA_TTS_AVAILABLE:
            print("[TTS Engine] Warning: 'sherpa_onnx' library not installed. Running in mock TTS mode.")
            return

        # Path resolution for VITS/MMS models
        vits_model = os.path.join(self.model_dir, "model.onnx")
        tokens = os.path.join(self.model_dir, "tokens.txt")
        lexicon = os.path.join(self.model_dir, "lexicon.txt")
        data_dir = os.path.join(self.model_dir, "espeak-ng-data")

        if not os.path.exists(vits_model):
            print(f"[TTS Engine] Warning: Model not found at '{vits_model}'. Download assets using setup_assets.py.")
            return

        try:
            vits_config = sherpa_onnx.OfflineTtsVitsModelConfig(
                model=vits_model,
                tokens=tokens,
                lexicon=lexicon if os.path.exists(lexicon) else "",
                data_dir=data_dir if os.path.exists(data_dir) else "",
                length_scale=1.0,
            )

            config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=vits_config,
                    provider="cpu",
                    num_threads=self.num_threads,
                ),
                max_num_sentences=1,
            )

            self.tts = sherpa_onnx.OfflineTts(config)
            print("[TTS Engine] Sherpa-ONNX MMS-VITS TTS loaded successfully.")
        except Exception as e:
            print(f"[TTS Engine] Error initializing Sherpa-ONNX TTS: {e}")

    def synthesize(self, text: str, sid: int = 0, speed: float = 1.0) -> Tuple[np.ndarray, int]:
        """
        Synthesizes text into PCM audio samples.
        Returns:
            Tuple of (audio_samples_float32, sample_rate)
        """
        if not text.strip():
            return np.zeros(0, dtype=np.float32), 22050

        start_time = time.time()

        if self.tts is not None:
            audio = self.tts.generate(text, sid=sid, speed=speed)
            samples = np.array(audio.samples, dtype=np.float32)
            sample_rate = audio.sample_rate
            rtf = (time.time() - start_time) / (len(samples) / sample_rate)
            print(f"[TTS Engine] Synthesized {len(text)} chars in {(time.time() - start_time)*1000:.1f}ms (RTF: {rtf:.3f})")
            return samples, sample_rate

        # Fallback / Mock audio generator for development without ONNX models
        sample_rate = 22050
        duration_sec = max(1.0, len(text) * 0.08)
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
        # Generate a gentle 440 Hz tone as mock audio
        samples = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        print(f"[TTS Engine Mock] Generated synthetic fallback audio tone ({duration_sec:.2f}s).")
        return samples, sample_rate


if __name__ == "__main__":
    engine = TTSEngine()
    audio_data, sr = engine.synthesize("Emergency message test.")
    print(f"[Test TTS Engine] Output shape: {audio_data.shape}, Sample Rate: {sr} Hz")