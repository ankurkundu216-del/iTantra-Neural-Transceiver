import queue
import struct
import threading
import numpy as np
import sounddevice as sd
import onnxruntime as ort
import sherpa_onnx
import time
import sys

# ==========================================
# SYSTEM ARCHITECTURE CONFIGURATIONS
# ==========================================
SAMPLE_RATE = 16000
CHANNELS = 1
VAD_CHUNK_SIZE = 512  # 32ms frames for Silero VAD
PAUSE_THRESHOLD_MS = 600
PAUSE_CHUNKS = int((PAUSE_THRESHOLD_MS / 1000) * (SAMPLE_RATE / VAD_CHUNK_SIZE))
VAD_THRESHOLD = 0.5

# Queues for thread-safe data transfer
audio_queue = queue.Queue()
stt_queue = queue.Queue()

# ==========================================
# MODULE 1: BINARY PACKETIZER
# ==========================================
def build_binary_packet(text: str, is_distress: bool = False, lang_code: int = 0x01) -> bytes:
    """
    Packs UTF-8 text into a strict 6-byte header payload.
    Header format: Magic (1B) | Priority (1B) | Lang (1B) | Length (2B uint16) | CRC/Reserved (1B)
    """
    payload = text.encode('utf-8')
    payload_len = len(payload)
    
    # Pack constraints: > (Big Endian), B (uint8), B, B, H (uint16), B
    magic_byte = 0x49  # 'I' for iTantra
    priority_flag = 0x01 if is_distress else 0x00
    reserved_crc = 0x00 # CRC checksum logic can be appended here
    
    header = struct.pack('>BBBHB', magic_byte, priority_flag, lang_code, payload_len, reserved_crc)
    packet = header + payload
    
    return packet

# ==========================================
# MODULE 2: TRANSPORT LAYER (MOCKED)
# ==========================================
def transmit_over_bluetooth(packet: bytes):
    """
    Mocks Bluetooth SPP / RFCOMM Socket transfer.
    Expects receiver to decode the exact 6-byte header structure.
    """
    print("\n" + "="*50)
    print(f"[BLUETOOTH SPP] Transmitting {len(packet)} bytes...")
    print(f"[HEX TRACE] Header: {packet[:6].hex()}")
    print(f"[PAYLOAD] Text: '{packet[6:].decode('utf-8')}'")
    print("="*50 + "\n")

# ==========================================
# MODULE 3: ASYNCHRONOUS STT WORKER
# ==========================================
def stt_worker_thread(recognizer):
    """
    Background thread dedicated to STT decoding. 
    Prevents CPU-heavy Sherpa-ONNX execution from blocking the continuous mic stream.
    """
    while True:
        # Block until a full sentence audio array is received from VAD
        audio_data = stt_queue.get()
        if audio_data is None: 
            break # Poison pill to exit thread
            
        print("[STT ENGINE] Processing audio chunk offline...")
        
        # Initialize streaming inference
        stream = recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, audio_data)
        
        # Execute decoding (C++ backend)
        start_t = time.time()
        recognizer.decode_stream(stream)
        text = stream.result.text.strip()
        latency = time.time() - start_t
        
        if text:
            print(f"[STT ENGINE] Decoded in {latency:.2f}s: {text}")
            # Packetize and Send
            binary_packet = build_binary_packet(text, is_distress=False, lang_code=0x01)
            transmit_over_bluetooth(binary_packet)
            
        # Free memory immediately (critical for sub-150MB target)
        del audio_data
        del stream
        stt_queue.task_done()

# ==========================================
# MODULE 4: AUDIO CAPTURE & VAD ENGINE
# ==========================================
def audio_callback(indata, frames, time, status):
    """ High-priority C-Thread callback pushing raw audio to VAD queue. """
    if status:
        print(status, file=sys.stderr)
    # Flatten and convert to float32
    audio_queue.put(indata.flatten().astype(np.float32))

def run_transceiver():
    print("[SYSTEM] Initializing iTantra Neural Transceiver (Sender)...")
    
    # 1. Load Silero VAD (ONNX)
    try:
        vad_session = ort.InferenceSession("assets/vad/silero_vad.onnx", providers=['CPUExecutionProvider'])
    except Exception as e:
        print(f"[ERROR] Silero VAD ONNX model not found: {e}")
        print("Please run 'python setup_assets.py' first.")
        sys.exit(1)
        
    # VAD State Variables (v3/v4 ONNX requirements)
    h = np.zeros((2, 1, 64), dtype=np.float32)
    c = np.zeros((2, 1, 64), dtype=np.float32)

    # 2. Load Sherpa-ONNX STT
    print("[SYSTEM] Loading INT8 STT Engine (Sherpa-ONNX Zipformer)...")
    try:
        stt_recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder="assets/stt/encoder-epoch-99-avg-1.onnx",
            decoder="assets/stt/decoder-epoch-99-avg-1.onnx",
            joiner="assets/stt/joiner-epoch-99-avg-1.onnx",
            tokens="assets/stt/tokens.txt",
            num_threads=1,          # Force 1 thread to limit CPU throttling on mobile
            sample_rate=SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search"
        )
    except Exception as e:
        print(f"[ERROR] Sherpa-ONNX models not found in 'assets/stt/': {e}")
        print("Please run 'python setup_assets.py' to download required weights.")
        sys.exit(1)

    # Start STT Worker Thread
    threading.Thread(target=stt_worker_thread, args=(stt_recognizer,), daemon=True).start()

    # 3. Main VAD Loop State
    is_speaking = False
    silence_chunks = 0
    sentence_buffer = []

    print(f"[SYSTEM] Ready. Listening on Microphone (Threshold: {PAUSE_THRESHOLD_MS}ms pause)...")
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=VAD_CHUNK_SIZE, callback=audio_callback):
        try:
            while True:
                # Get exact 512-sample chunk
                chunk = audio_queue.get()
                
                # Execute ONNX VAD
                vad_input = {'input': chunk.reshape(1, -1), 'sr': np.array([SAMPLE_RATE], dtype=np.int64), 'h': h, 'c': c}
                vad_out, h, c = vad_session.run(None, vad_input)
                speech_prob = vad_out[0][0]

                if speech_prob > VAD_THRESHOLD:
                    if not is_speaking:
                        print("[VAD] Speech Detected. Buffering...")
                    is_speaking = True
                    silence_chunks = 0
                    sentence_buffer.append(chunk)
                else:
                    if is_speaking:
                        silence_chunks += 1
                        sentence_buffer.append(chunk)
                        
                        # Check if silence threshold exceeded
                        if silence_chunks >= PAUSE_CHUNKS:
                            print("[VAD] Sentence boundary reached. Sending to STT.")
                            full_sentence = np.concatenate(sentence_buffer)
                            
                            # Push to background STT thread to prevent blocking Mic
                            stt_queue.put(full_sentence)
                            
                            # Reset states
                            is_speaking = False
                            silence_chunks = 0
                            sentence_buffer = []
                            
        except KeyboardInterrupt:
            print("\n[SYSTEM] Shutting down...")

if __name__ == "__main__":
    run_transceiver()