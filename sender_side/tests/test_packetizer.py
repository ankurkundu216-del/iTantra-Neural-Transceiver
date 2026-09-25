"""
Test Binary Packetizer
Validates binary frame creation, 6-byte header packing, and metadata unpacking.
"""
import sys
import struct
from pathlib import Path

# Adjust path to import from parent core directory
sys.path.append(str(Path(__file__).parent.parent))

from core.binary_packetizer import BinaryPacketizer

def test_packetizer():
    print("=" * 50)
    print(" TEST: Binary Packetizer & Header Verification")
    print("=" * 50)
    
    test_text = "SOS Need medical assistance at sector 4"
    is_distress = True
    lang_code = 1  # English
    
    # 1. Create packet
    packet = BinaryPacketizer.create_packet(test_text, is_distress=is_distress, lang_code=lang_code)
    
    # 2. Extract and parse Header
    header = packet[:6]
    payload = packet[6:]
    
    magic, priority, lang, length, reserved = struct.unpack('>BBBHB', header)
    decoded_text = payload.decode('utf-8')
    
    print(f"[PACKET] Total Size: {len(packet)} bytes")
    print(f"[HEADER] Hex: {header.hex()}")
    print(f"  - Magic Byte : {hex(magic)} (Expected: 0x49)")
    print(f"  - Priority   : {priority} (Distress Flag)")
    print(f"  - Lang Code  : {lang}")
    print(f"  - Length     : {length} bytes")
    print(f"[PAYLOAD] Text : '{decoded_text}'")
    
    # Assertions
    assert magic == 0x49, f"Invalid magic byte: {hex(magic)}"
    assert priority == 0x01, "Distress flag failed to pack correctly"
    assert length == len(test_text.encode('utf-8')), "Payload length mismatch"
    assert decoded_text == test_text, "Payload text corrupted during encoding/decoding"
    
    print("[PASSED] Binary Packetizer structure verified successfully.\n")

if __name__ == "__main__":
    test_packetizer()