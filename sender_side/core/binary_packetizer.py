"""
Binary Packetizer Module
Packs UTF-8 text into a highly compressed binary frame with a 6-byte header.
"""
import struct

class BinaryPacketizer:
    MAGIC_BYTE = 0x49  # 'I' for iTantra

    @classmethod
    def create_packet(cls, text: str, is_distress: bool = False, lang_code: int = 1) -> bytes:
        """
        Packs text into a 50-100 byte payload frame.
        Header: Magic (1B) | Priority (1B) | Lang (1B) | Length (2B) | Reserved (1B)
        """
        payload = text.encode('utf-8')
        payload_length = len(payload)
        
        if payload_length > 65535:
            # Enforce unsigned 16-bit integer limit (though sentences will rarely exceed 100 bytes)
            payload = payload[:65535]
            payload_length = 65535

        priority_flag = 0x01 if is_distress else 0x00
        reserved_crc = 0x00
        
        # '>BBBHB' = Big-Endian, uint8, uint8, uint8, uint16, uint8
        header = struct.pack('>BBBHB', 
                             cls.MAGIC_BYTE, 
                             priority_flag, 
                             lang_code, 
                             payload_length, 
                             reserved_crc)
        
        return header + payload