"""
Silero VAD Module
Processes continuous audio chunks and isolates sentences using a 600ms pause threshold.
"""
import numpy as np
import onnxruntime as ort

class VADDetector:
    def __init__(self, model_path: str = "assets/vad/silero_vad.onnx", sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.threshold = 0.5
        # 600ms pause threshold translated to chunks (Assuming 512 samples/chunk = 32ms)
        self.pause_chunks_threshold = int((0.6 * sample_rate) / 512) 
        
        # Load ONNX Session (Strictly CPU for edge constraints)
        sess_options = ort.SessionOptions()
        sess_options.inter_op_num_threads = 1
        sess_options.intra_op_num_threads = 1
        self.session = ort.InferenceSession(model_path, sess_options, providers=['CPUExecutionProvider'])
        
        self.reset_state()

    def reset_state(self):
        """Resets the internal state of the Silero VAD model."""
        self.h = np.zeros((2, 1, 64), dtype=np.float32)
        self.c = np.zeros((2, 1, 64), dtype=np.float32)

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Runs inference on a single audio chunk and returns True if speech is detected."""
        # Silero VAD expects input shape: (batch_size, sequence_length)
        ort_inputs = {
            'input': np.expand_dims(audio_chunk, axis=0),
            'sr': np.array([self.sample_rate], dtype=np.int64),
            'h': self.h,
            'c': self.c
        }
        ort_outs = self.session.run(None, ort_inputs)
        speech_prob = ort_outs[0][0][0]
        
        # Update hidden states for the next chunk
        self.h, self.c = ort_outs[1], ort_outs[2]
        
        return speech_prob > self.threshold