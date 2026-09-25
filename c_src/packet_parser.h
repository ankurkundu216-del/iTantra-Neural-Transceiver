#ifndef PACKET_PARSER_H
#define PACKET_PARSER_H

#include <cstdint>

#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

struct ParsedPacketResult {
    bool success;
    bool is_distress;
    uint8_t language_code;
    uint16_t payload_length;
    uint8_t received_checksum;
    uint8_t calculated_checksum;
    const char* text_data;
    const char* error_message;
};

/**
 * Native C++ packet frame unpacker.
 * Inspects Magic Byte, validates XOR CRC checksum over header+payload, 
 * and parses priority flags.
 */
EXPORT ParsedPacketResult parse_binary_frame(const uint8_t* raw_bytes, size_t total_length);

/**
 * Free dynamically allocated strings returned by the parser.
 */
EXPORT void free_packet_result(ParsedPacketResult result);

}

#endif // PACKET_PARSER_H