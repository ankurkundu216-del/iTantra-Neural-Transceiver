#include "packet_parser.h"
#include <cstring>
#include <cstdlib>

constexpr uint8_t MAGIC_BYTE = 0x49; // 'I' for iTantra

extern "C" {

EXPORT ParsedPacketResult parse_binary_frame(const uint8_t* raw_bytes, size_t total_length) {
    ParsedPacketResult res;
    std::memset(&res, 0, sizeof(ParsedPacketResult));

    // 1. Frame Underflow Check (6-byte header minimum)
    if (total_length < 6) {
        res.success = false;
        res.error_message = strdup("Frame underflow: Byte buffer smaller than 6-byte header.");
        return res;
    }

    // 2. Magic Byte Inspection
    uint8_t magic = raw_bytes[0];
    if (magic != MAGIC_BYTE) {
        res.success = false;
        res.error_message = strdup("Invalid Magic Byte: Packet header corrupted.");
        return res;
    }

    // 3. Header Unpacking (Big-Endian Short for Payload Length)
    uint8_t priority = raw_bytes[1];
    uint8_t lang_code = raw_bytes[2];
    uint16_t payload_len = (static_cast<uint16_t>(raw_bytes[3]) << 8) | raw_bytes[4];
    uint8_t rx_checksum = raw_bytes[5];

    // 4. Full Length Verification
    if (total_length < static_cast<size_t>(6 + payload_len)) {
        res.success = false;
        res.error_message = strdup("Truncated frame payload: Expected more bytes based on header.");
        return res;
    }

    // 5. Native Bitwise XOR Checksum Calculation
    uint8_t calculated_crc = 0x00;
    
    // Header partial bytes (magic, priority, lang, payload_len MSB, payload_len LSB)
    for (size_t i = 0; i < 5; ++i) {
        calculated_crc ^= raw_bytes[i];
    }

    // Payload bytes
    const uint8_t* payload_ptr = raw_bytes + 6;
    for (size_t i = 0; i < payload_len; ++i) {
        calculated_crc ^= payload_ptr[i];
    }

    // 6. Checksum Integrity Guard
    if (calculated_crc != rx_checksum) {
        res.success = false;
        res.received_checksum = rx_checksum;
        res.calculated_checksum = calculated_crc;
        res.error_message = strdup("CRC Checksum Failed: Bitflip detected in payload transmission.");
        return res;
    }

    // 7. Extract UTF-8 Payload String
    char* text_buffer = static_cast<char*>(std::malloc(payload_len + 1));
    std::memcpy(text_buffer, payload_ptr, payload_len);
    text_buffer[payload_len] = '\0';

    res.success = true;
    res.is_distress = (priority & 0x01) != 0;
    res.language_code = lang_code;
    res.payload_length = payload_len;
    res.received_checksum = rx_checksum;
    res.calculated_checksum = calculated_crc;
    res.text_data = text_buffer;
    res.error_message = nullptr;

    return res;
}

EXPORT void free_packet_result(ParsedPacketResult result) {
    if (result.text_data) {
        std::free(const_cast<char*>(result.text_data));
    }
    if (result.error_message) {
        std::free(const_cast<char*>(result.error_message));
    }
}

}