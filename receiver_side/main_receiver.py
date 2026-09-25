"""
iTantra Neural Transceiver - Receiver Main Entry Point
Orchestrates transport listeners, frame depacketizing, priority audio routing, and offline TTS.
"""

import sys
import time
import signal
from pathlib import Path

# Add project root to Python module search path
sys.path.append(str(Path(__file__).parent.parent))

from receiver_side.core.binary_depacketizer import BinaryDepacketizer, PacketData
from receiver_side.core.tts_engine import TTSEngine
from receiver_side.core.audio_player import AudioPlayer
from receiver_side.transport.bt_receiver import BluetoothReceiver
from receiver_side.transport.wifi_direct_receiver import WiFiDirectReceiver


class TransceiverReceiverApp:
    def __init__(self, bt_port: int = 1, wifi_port: int = 9999):
        print("==========================================")
        print("    iTantra Neural Transceiver (Receiver) ")
        print("==========================================\n")
        
        # Initialize Core Engines
        print("⚙️ Initializing Offline TTS Engine & Audio Pipeline...")
        self.tts = TTSEngine()
        self.player = AudioPlayer()

        # Initialize Transport Listeners
        self.bt_receiver = BluetoothReceiver(port=bt_port, on_frame_received=self.handle_incoming_frame)
        self.wifi_receiver = WiFiDirectReceiver(port=wifi_port, on_frame_received=self.handle_incoming_frame)

        self.is_running = False

    def handle_incoming_frame(self, raw_frame: bytes) -> None:
        """
        Stream Processing Callback Pipeline:
        1. Depacketize frame & verify XOR CRC
        2. Inspect priority flag (Distress vs Normal)
        3. Synthesize speech via MMS-VITS TTS
        4. Trigger non-blocking audio playback with priority preemption
        """
        start_time = time.time()

        # 1. Depacketize & Verify Integrity
        success, packet, err = BinaryDepacketizer.unpack(raw_frame)
        if not success:
            print(f"❌ [Receiver Error] {err}")
            return

        priority_label = "🚨 DISTRESS (HIGH PRIORITY)" if packet.is_distress else "🟢 NORMAL"
        print(f"\n📩 [Frame Ingested] {priority_label}")
        print(f" ├─ Payload: '{packet.text}'")
        print(f" └─ Length: {packet.payload_length} bytes | Lang Code: {packet.language_code}")

        # 2. Synthesize Speech
        audio_samples, sample_rate = self.tts.synthesize(packet.text)

        # 3. Route Audio (Priority Preemption)
        self.player.play(audio_samples, sample_rate=sample_rate, is_distress=packet.is_distress)

        latency_ms = (time.time() - start_time) * 1000
        print(f"⚡ [E2E Receiver Processing Latency] {latency_ms:.1f} ms")

    def start(self) -> None:
        """Starts transport socket listeners and enters event loop."""
        self.is_running = True
        
        print("\n🚀 Starting Transport Listeners...")
        self.bt_receiver.start()
        self.wifi_receiver.start()

        print("\n✅ Receiver online and waiting for inbound transmissions. Press Ctrl+C to stop.\n")

        try:
            while self.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Gracefully shuts down all listeners and audio streams."""
        print("\n🛑 Shutting down Transceiver Receiver...")
        self.is_running = False
        self.bt_receiver.stop()
        self.wifi_receiver.stop()
        self.player.stop()
        print("👋 Receiver safely terminated.")


def main():
    app = TransceiverReceiverApp()
    
    # Handle termination signals cleanly
    def signal_handler(sig, frame):
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app.start()


if __name__ == "__main__":
    main()