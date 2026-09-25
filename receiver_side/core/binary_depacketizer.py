"""
Binary Depacketizer Engine
Executes frame unpacking via C++ Native Shared Library (`libpacket_parser`) 
with pure-Python fallback support.
"""

import ctypes
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

MAGIC_BYTE = 0x49  # 'I' for iTantra


@dataclass
class PacketData:
    is_distress: bool
    language_code: int
    payload_length: int
    checksum: int
    text: str


# --- CTYPES C++ STRUCT BINDINGS ---
class CtxParsedResult(ctypes.Structure):
    _fields_ = [
        ("success", ctypes.c_bool),
        ("is_distress", ctypes.c_bool),
        ("language_code", ctypes.c_uint8),
        ("payload_length", ctypes.c_uint16),
        ("received_checksum", ctypes.c_uint8),
        ("calculated_checksum", ctypes.c_uint8),
        ("text_data", ctypes.c_char_p),
        ("error_message", ctypes.c_char_p),
    ]


# Locate and load native C++ shared library if compiled
_cpp_lib = None
lib_dir = Path(__file__).parent
lib_name = "libpacket_parser.dll" if sys.platform.startswith("win") else "libpacket_parser.so"
lib_path = lib_dir / lib_name

if lib_path.exists():
    try:
        _cpp_lib = ctypes.CDLL(str(lib_path))
        _cpp_lib.parse_binary_frame.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        _cpp_lib.parse_binary_frame.restype = CtxParsedResult
        _cpp_lib.free_packet_result.argtypes = [CtxParsedResult]
        _cpp_lib.free_packet_result.restype = None
        print(f"⚡ [BinaryDepacketizer] Loaded native C++ backend: {lib_name}")
    except Exception as e:
        print(f"⚠️ [BinaryDepacketizer] Could not load native C++ library ({e}). Using Python fallback.")


class BinaryDepacketizer:
    @classmethod
    def unpack(cls, raw_frame: bytes) -> Tuple[bool, Optional[PacketData], Optional[str]]:
        """
        Unpacks binary frame. Prefers C++ native runtime engine; falls back to Python.
        """
        if _cpp_lib is not None:
            return cls._unpack_cpp(raw_frame)
        return cls._unpack_python(raw_frame)

    @classmethod
    def _unpack_cpp(cls, raw_frame: bytes) -> Tuple[bool, Optional[PacketData], Optional[str]]:
        """Direct C++ ABI Execution Path."""
        frame_len = len(raw_frame)
        c_bytes = (ctypes.c_uint8 * frame_len).from_buffer(bytearray(raw_frame))

        res = _cpp_lib.parse_binary_frame(c_bytes, frame_len)

        try:
            if not res.success:
                err_msg = res.error_message.decode('utf-8') if res.error_message else "Unknown C++ Parsing Error"
                return False, None, err_msg

            text = res.text_data.decode('utf-8', errors='replace') if res.text_data else ""
            packet = PacketData(
                is_distress=res.is_distress,
                language_code=res.language_code,
                payload_length=res.payload_length,
                checksum=res.received_checksum,
                text=text
            )
            return True, packet, None
        finally:
            _cpp_lib.free_packet_result(res)

    @classmethod
    def _unpack_python(cls, raw_frame: bytes) -> Tuple[bool, Optional[PacketData], Optional[str]]:
        """Pure Python Fallback Execution Path."""
        if len(raw_frame) < 6:
            return False, None, "Frame underflow: Minimum 6-byte header required."

        magic, priority, lang_code, payload_len, rx_checksum = struct.unpack('>BBBHB', raw_frame[:6])

        if magic != MAGIC_BYTE:
            return False, None, f"Invalid Magic Byte: Received {hex(magic)}, expected {hex(MAGIC_BYTE)}."

        if len(raw_frame) < 6 + payload_len:
            return False, None, f"Truncated frame: Expected {6 + payload_len} bytes, got {len(raw_frame)}."

        payload_bytes = raw_frame[6:6 + payload_len]

        # Calculate XOR checksum
        calc_checksum = 0x00
        for b in raw_frame[:5]:
            calc_checksum ^= b
        for b in payload_bytes:
            calc_checksum ^= b

        if calc_checksum != rx_checksum:
            return False, None, f"CRC Checksum Failed: Computed {hex(calc_checksum)}, received {hex(rx_checksum)}."

        text = payload_bytes.decode('utf-8', errors='replace')
        packet = PacketData(
            is_distress=bool(priority & 0x01),
            language_code=lang_code,
            payload_length=payload_len,
            checksum=rx_checksum,
            text=text
        )
        return True, packet, None