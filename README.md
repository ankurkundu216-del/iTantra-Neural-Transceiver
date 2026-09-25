# ⚡ iTantra Neural Transceiver 📡

> **Edge-Native, Off-Grid P2P Neural Audio Transceiver**  
> *Sub-second voice translation over compressed neural frames for off-grid tactical and emergency communications.*

---

## 📸 System Overview

**iTantra Neural Transceiver** is a real-time, peer-to-peer audio communication architecture designed to operate in total infrastructure blackouts (disaster zones, defense operations, zero-cellular environments). 

Instead of streaming bandwidth-heavy raw audio over fragile RF links, iTantra captures live speech, transcribes it locally using **INT8 Quantized Neural Models**, packs it into a high-density binary payload with **bitwise C++ CRC verification**, streams it over **Bluetooth / Wi-Fi Direct**, and synthesizes it back to natural regional voice on the receiver end.

---

## 🔥 Key Technical Innovations

* **⚡ Sub-1.2s End-to-End Latency:** Operates under extreme packet constraints (50–100 Bytes per sentence payload).
* **🧠 Off-Grid Neural Pipeline:** Zero cloud reliance. Runs INT8 Quantized **Zipformer Transducer (STT)** and **MMS-VITS (TTS)** locally via ONNX runtimes.
* **🚀 Native C++ Bitwise Engine:** Hardware-accelerated C++ frame parser utilizing bitwise XOR CRC validation for zero-copy binary unpacking.
* **🚨 Priority Distress Audio Override:** Emergency signals automatically override silent profiles, set stream volume to 100%, and trigger immediate alert playback.
* **📡 Dual P2P Transport Layer:** Seamless fallback and routing across **Bluetooth RFCOMM (SPP)** and high-speed **Wi-Fi Direct TCP sockets**.

---

## 🏗️ End-to-End Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PHONE A : SENDER SIDE                           │
│                                                                        │
│  [ Microphone ] ──> [ Silero VAD ] ──> [ Sherpa-ONNX Zipformer STT ]   │
│  (16kHz PCM)        (Sentence Cut)     (INT8 Neural Transducer)        │
│                                                   │                    │
│                                                   ▼                    │
│  [ BT / Wi-Fi Direct ] <── [ Binary Header Packetizer (6-Byte HDR) ]   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                           P2P Data Payload
                          (50 - 100 Bytes)
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│                       PHONE B : RECEIVER SIDE                          │
│                                                                        │
│  [ BT / Wi-Fi Reader ] ──> [ Native C++ Parser (libpacket_parser) ]    │
│                            (Bitwise XOR CRC Check & Priority Flag)     │
│                                                   │                    │
│                                                   ▼                    │
│  [ Speaker Playback ]  <── [ MMS-VITS TTS ] <── [ Priority Routing ]   │
│  (Forced Override)         (Neural Synthesis)   (Distress Handler)     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Binary Header Frame Protocol

> **All P2P packet exchanges enforce a strict, byte-packed 6-byte binary header followed by a UTF-8 encoded text payload.**

### 1. Packet Memory Layout

0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Magic (0x49) | Priority Flag | Language Code | Payload Len H |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Payload Len L |  Checksum XOR | Payload Data (UTF-8 Bytes...) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

### 2. C Structure Memory Definition
```C
#pragma pack(push, 1)
typedef struct {
    uint8_t  magic_byte;     // Always 0x49 ('I')
    uint8_t  priority_flag;   // 0x00 = Standard, 0x01 = Emergency Distress
    uint8_t  lang_code;       // 0x01 = EN, 0x02 = HI, etc.
    uint16_t payload_len;     // Big-Endian payload size (bytes)
    uint8_t  checksum;        // Bitwise XOR over Header[0..4] + Payload
} PacketHeader;
#pragma pack(pop)
```

### 3. Header Specification Table

| Offset | Field Name | Type | Size | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x00` | **Magic Byte** | `uint8_t` | 1 Byte | Header validation signature (`0x49` / ASCII `'I'`) |
| `0x01` | **Priority Flag** | `uint8_t` | 1 Byte | `0x00` (Normal) or `0x01` (Emergency Override) |
| `0x02` | **Language Code** | `uint8_t` | 1 Byte | Dialect routing ID for Receiver TTS synthesis |
| `0x03` | **Payload Length** | `uint16_t` | 2 Bytes | Big-Endian byte length (*N*) of trailing text payload |
| `0x05` | **Checksum** | `uint8_t` | 1 Byte | Hardware XOR CRC calculated across entire frame |
| `0x06` | **Payload** | `char[]` | *N* Bytes | Raw UTF-8 encoded transcribed speech string |

---

## 📂 Repository Structure
```text
iTantra-Neural-Transceiver/
├── .gitignore                         # Excludes virtualenvs, build artifacts, and ONNX models
├── README.md                          # Project documentation & execution guide
├── build_cpp.py                       # Cross-platform compiler wrapper (g++ / MSVC)
│
├── c_src/                             # Native High-Performance C++ Core
│   ├── packet_parser.h                # C-ABI packed struct definitions & function export macros
│   └── packet_parser.cpp              # Bitwise XOR CRC validation & zero-copy parser engine
│
├── sender_side/                       # Transmitter Node Architecture
│   ├── main_sender.py                 # Live voice capture & transmission pipeline entry point
│   ├── setup_assets.py                # Asset engine: Auto-fetches Sherpa-ONNX & Silero models
│   ├── requirements.txt               # Sender dependencies (sounddevice, sherpa-onnx, etc.)
│   ├── assets/                        # Local Neural Weights Directory
│   │   ├── stt/                       # INT8 Quantized Zipformer transducer models
│   │   └── vad/                       # Silero VAD ONNX voice detection binary
│   ├── core/                          # Audio Processing Subsystems
│   │   ├── __init__.py                # Package initialization
│   │   ├── mic_stream.py              # Non-blocking C-thread 16kHz PCM mic buffer listener
│   │   ├── vad_detector.py            # Low-latency speech boundary detector (Silero)
│   │   ├── stt_engine.py              # On-device Sherpa-ONNX speech recognition parser
│   │   └── binary_packetizer.py       # Custom 6-byte header packer & XOR CRC generator
│   ├── transport/                     # Wireless P2P Transmitter Interfaces
│   │   ├── __init__.py                # Package initialization
│   │   ├── bt_sender.py               # Bluetooth RFCOMM / SPP raw socket writer
│   │   └── wifi_direct_sender.py      # High-bandwidth Wi-Fi Direct TCP client
│   └── tests/                         # Sender Testing & Emulation Suite
│       ├── test_mic.py                # Hardware mic input monitor and level meter
│       ├── test_packetizer.py         # Unit tests for binary packing integrity
│       └── mock_sender_stream.py      # Stream simulator emitting test voice frames
│
└── receiver_side/                     # Receiver Node Architecture
    ├── main_receiver.py               # P2P listener & voice playback pipeline entry point
    ├── setup_assets.py                # Asset engine: Auto-fetches MMS-VITS synthesis models
    ├── requirements.txt               # Receiver dependencies (sounddevice, scipy, numpy)
    ├── core/                          # Synthesis & Processing Subsystems
    │   ├── __init__.py                # Package initialization
    │   ├── binary_depacketizer.py     # Ctypes interface binding to compiled libpacket_parser
    │   ├── tts_engine.py              # MMS-VITS offline neural text-to-speech engine
    │   ├── audio_player.py            # Priority-aware audio output device router
    │   └── libpacket_parser.dll       # Compiled native shared library (Windows DLL / Linux SO)
    ├── transport/                     # Wireless P2P Receiver Interfaces
    │   ├── __init__.py                # Package initialization
    │   ├── bt_receiver.py             # Bluetooth RFCOMM socket listener server
    │   └── wifi_direct_receiver.py    # Wi-Fi Direct TCP server socket handler
    └── tests/                         # Receiver Verification Suite
        ├── test_depacketizer.py       # C++ Ctypes wrapper & CRC validation tests
        └── test_player.py             # Priority audio override & distress signal tests
```

---

## ⚡ Quick Start & Execution Guide

### 1. Clone & Build C++ Native Parser Engine
```bash
# Clone repository
git clone [https://github.com/ankurkundu216-del/iTantra-Neural-Transceiver.git](https://github.com/ankurkundu216-del/iTantra-Neural-Transceiver.git)
cd iTantra-Neural-Transceiver

# Compile the high-speed C++ frame parser shared library
python build_cpp.py
```

### 2. Configure & Fetch Neural Models
```bash
# Setup Sender Environment & Neural Models
cd sender_side
pip install -r requirements.txt
python setup_assets.py
cd ..

# Setup Receiver Environment & Synthetic Voice Models
cd receiver_side
pip install -r requirements.txt
python setup_assets.py
cd ..
```

---

## 🧪 Verification & End-to-End Simulation
Run verification tests across core systems:
```bash
# 1. Test Native C++ Unpacking & Bitwise CRC Validation
python -m receiver_side.tests.test_depacketizer

# 2. Test Priority Audio Override Router
python -m receiver_side.tests.test_player

# 3. Test Binary Header Packaging Logic
python -m sender_side.tests.test_packetizer
```

### Run Full End-to-End Pipeline (Two Terminals)
#### Terminal 1 (Receiver Node):
```bash
python -m receiver_side.main_receiver
```
#### Terminal 2 (Simulated Sender Stream):
```bash
python -m sender_side.tests.mock_sender_stream
```
