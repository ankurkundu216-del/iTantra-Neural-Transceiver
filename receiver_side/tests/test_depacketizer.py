"""
Unit tests for Binary Depacketizer.
Validates frame unpacking, magic byte security, CRC calculation, and error resilience.
"""

import sys
import struct
from pathlib import Path

# Add project root to path for module imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from receiver_side.core.binary_depacketizer import BinaryDepacketizer, MAGIC_BYTE


def build_frame(magic: int, priority: int, lang: int, text: str, tamper_crc: bool = False) -> bytes:
    """Helper utility to assemble valid/invalid raw binary frames."""
    payload = text.encode('utf-8')
    payload_len = len(payload)
    hdr_partial = struct.pack('>BBBH', magic, priority, lang, payload_len)
    
    # Calculate XOR checksum
    checksum = 0x00
    for b in hdr_partial:
        checksum ^= b
    for b in payload:
        checksum ^= b

    if tamper_crc:
        checksum ^= 0xFF  # Corrupt checksum

    return hdr_partial + bytes([checksum]) + payload


def test_valid_packet():
    print("[Test 1] Valid Normal Frame Unpacking...")
    raw = build_frame(MAGIC_BYTE, 0, 1, "Hello World from Sender")
    success, packet, err = BinaryDepacketizer.unpack(raw)
    
    assert success is True, f"Failed: {err}"
    assert packet.is_distress is False
    assert packet.language_code == 1
    assert packet.text == "Hello World from Sender"
    print("  └─ PASSED ✅")


def test_distress_flag():
    print("[Test 2] Distress Flag Detection...")
    raw = build_frame(MAGIC_BYTE, 1, 1, "SOS Emergency Signal!")
    success, packet, err = BinaryDepacketizer.unpack(raw)
    
    assert success is True, f"Failed: {err}"
    assert packet.is_distress is True
    assert packet.text == "SOS Emergency Signal!"
    print("  └─ PASSED ✅")


def test_invalid_magic_byte():
    print("[Test 3] Rejection of Invalid Magic Byte...")
    raw = build_frame(0x99, 0, 1, "Invalid frame")
    success, packet, err = BinaryDepacketizer.unpack(raw)
    
    assert success is False
    assert "Invalid Magic Byte" in err
    print(f"  └─ PASSED ✅ (Caught expected error: {err})")


def test_corrupted_checksum():
    print("[Test 4] Rejection of Corrupted CRC Checksum...")
    raw = build_frame(MAGIC_BYTE, 0, 1, "Integrity Check Text", tamper_crc=True)
    success, packet, err = BinaryDepacketizer.unpack(raw)
    
    assert success is False
    assert "CRC Checksum Failed" in err
    print(f"  └─ PASSED ✅ (Caught expected error: {err})")


def test_truncated_frame():
    print("[Test 5] Frame Underflow/Truncation Handling...")
    raw = bytes([0x49, 0x00, 0x01])  # Only 3 bytes instead of 6+
    success, packet, err = BinaryDepacketizer.unpack(raw)
    
    assert success is False
    assert "Frame underflow" in err
    print(f"  └─ PASSED ✅ (Caught expected error: {err})")


def run_all_tests():
    print("==========================================")
    print(" RUNNING BINARY DEPACKETIZER TEST SUITE   ")
    print("==========================================\n")
    test_valid_packet()
    test_distress_flag()
    test_invalid_magic_byte()
    test_corrupted_checksum()
    test_truncated_frame()
    print("\nAll Depacketizer tests completed successfully! 🎉")


if __name__ == "__main__":
    run_all_tests()