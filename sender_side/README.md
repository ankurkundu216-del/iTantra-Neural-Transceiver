# iTantra Neural Transceiver (Sender Mode - Phone A)
**Smart India Hackathon (SIH)**

A highly optimized, completely offline edge ML pipeline to capture voice, perform dynamic voice activity detection (VAD), infer text locally via INT8-quantized STT, and pack the data into an ultra-low bandwidth binary frame for P2P transmission.

## 🧠 System Architecture (Sender Side)

```text
[Continuous Audio Capture] ──► [Silero VAD (600ms boundary)] 
(16 kHz Mono PCM, C-Thread)    (Zero-latency ONNX Runtime)
                                          │
                                          ▼
[Bluetooth SPP Socket] ◄── [6-Byte Binary Packetizer] ◄── [Sherpa-ONNX STT Worker]
(Zero-Cloud Transfer)      (Magic, Priority, Text Data)   (INT8 Zipformer, Async)
```
## 🎯 SIH Metric Alignments
| SIH Requirement | Our Implementation Strategy |
| :--- | :--- |
| **Complete Offline Working** | [cite_start]Uses local `onnxruntime` and `sherpa-onnx`[cite: 20, 39]. Zero HTTP/Cloud API calls exist in the codebase. |
| **High Efficiency (<150MB)** | [cite_start]Memory is strictly managed via C++ JNI bindings[cite: 57]. Buffer references are deleted (`del`) immediately after STT decoding. |
| **Minimal Latency (<1.2s)** | Multithreaded architecture prevents mic blocking. [cite_start]STT runs concurrently asynchronously; payload size maxes out at ~100 bytes[cite: 52, 57]. |

## ⚙️ Setup & Execution

### 1. Install Dependencies
We rely purely on edge-optimized frameworks. Ensure you have Python 3.9+ installed.
```bash
pip install -r requirements.txt
```

### 2. Download Model Assets (Critical)
To meet the "No Internet" requirement, model weights must be pre-loaded into the assets/ directory.
#### A. Silero VAD (Voice Activity Detection)
```bash
mkdir -p assets/
wget [https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx](https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx) -O assets/silero_vad.onnx
```
#### B. Sherpa-ONNX STT (Zipformer INT8)
Download a pre-quantized streaming Zipformer model from the official k2-fsa repository and place the files inside assets/stt/:

encoder.onnx

decoder.onnx

joiner.onnx

tokens.txt

### 3. Run the Transceiver (Mock Mode)
To test the pipeline without a physical secondary Bluetooth device, run the main engine. The system will activate your microphone, detect your sentences in real-time, process the STT offline, and print the raw hexadecimal binary output to the terminal.
```bash
python main_sender.py
```