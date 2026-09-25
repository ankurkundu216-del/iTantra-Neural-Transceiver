# iTantra Neural Transceiver 🛰️⚡

An edge-native, off-grid neural audio transceiver designed for low-latency voice capture, local speech-to-text processing, binary packetization, and peer-to-peer transport over Bluetooth RFCOMM and Wi-Fi Direct.

---

## 🏗️ System Architecture

```text
  ┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
  │ Audio Capture   │ ───>  │ Silero VAD      │ ───>  │ Sherpa-ONNX STT  │
  │ (16kHz PCM Mic) │       │ (ONNX Engine)   │       │ (Zipformer INT8) │
  └─────────────────┘       └─────────────────┘       └──────────────────┘
                                                               │
  ┌─────────────────┐       ┌─────────────────┐                │
  │ P2P Transport   │ <───  │ Binary Header   │ <──────────────┘
  │ (BT / Wi-Fi P2P)│       │ Packetizer      │
  └─────────────────┘       └─────────────────┘
```

## ✨ Features
1. Continuous Microphone Streaming: Non-blocking C-thread raw audio   
buffer capture via sounddevice.

2. Neural Voice Activity Detection (VAD): Low-latency speech boundary detection powered by Silero VAD (ONNX).

3. Offline Speech-to-Text (STT): On-device INT8 quantized Zipformer transducer decoding via sherpa-onnx backend.

4. Strict Binary Packetization: Packs text into binary payloads with a custom 6-byte header:
Magic Byte (0x49) | Priority Flag | Language Code | Payload Length (uint16) | Checksum/Reserved

5. Peer-to-Peer Transport: Integrated support for Bluetooth SPP / RFCOMM sockets and high-bandwidth Wi-Fi Direct P2P channels.

---

## 📂 Project Structure
```text
    iTantra-Neural-Transceiver/
├── .gitignore
├── README.md
└── sender_side/
    ├── assets/                  # Neural model weights
    │   ├── stt/                 # Sherpa-ONNX Zipformer models & vocabulary
    │   └── vad/                 # Silero VAD ONNX model
    ├── core/                    # Core audio processing modules
    │   ├── __init__.py
    │   ├── binary_packetizer.py
    │   ├── mic_stream.py
    │   ├── stt_engine.py
    │   └── vad_detector.py
    ├── transport/               # P2P communication layers
    │   ├── __init__.py
    │   ├── bt_sender.py
    │   └── wifi_direct_sender.py
    ├── tests/                   # Verification and test suites
    │   ├── mock_sender_stream.py
    │   ├── test_mic.py
    │   └── test_packetizer.py
    ├── main_sender.py           # Main sender pipeline execution entry point
    ├── setup_assets.py          # Automated model downloader
    └── requirements.txt         # Project dependencies
```

## 🚀 Getting Started
1. Prerequisites
Ensure Python 3.10+ is installed on your system along with PortAudio dependencies (if running on Linux/Debian):
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

2. Installation
Clone the repository and install required dependencies:
```bash
git clone [https://github.com/ankurkundu216-del/iTantra-Neural-Transceiver.git](https://github.com/ankurkundu216-del/iTantra-Neural-Transceiver.git)
cd iTantra-Neural-Transceiver/sender_side
pip install -r requirements.txt
```

3. Download Model Assets
Fetch all ONNX neural weights and vocabulary binaries automatically:
```bash
python setup_assets.py
```

4. Running the Transceiver
Start the continuous sender pipeline:

```bash
python main_sender.py
```

## 🧪 Testing
Run unit and integration test scripts from the sender_side/ folder:

```bash
# Test physical microphone capture & audio level monitoring
python -m tests.test_mic

# Validate binary header packing and unpacking logic
python -m tests.test_packetizer

# Run end-to-end mock signal processing pipeline
python -m tests.mock_sender_stream
```