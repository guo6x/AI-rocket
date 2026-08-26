#include "relay_router.h"

#include <string.h>

RelayCommandResult RelayRouter::validateCommandDatagram(
    const uint8_t* input, size_t length, char* output, size_t output_size) {
    if (!input || !output || output_size == 0 || length == 0) {
        return RELAY_COMMAND_EMPTY;
    }
    if (length > MAX_COMMAND_BYTES || length >= output_size) {
        return RELAY_COMMAND_OVERLONG;
    }

    size_t start = 0;
    size_t end = length;
    while (start < end && (input[start] == ' ' || input[start] == '\t')) start++;
    while (end > start && (input[end - 1] == ' ' || input[end - 1] == '\t')) end--;
    if (start == end) return RELAY_COMMAND_EMPTY;

    for (size_t index = start; index < end; ++index) {
        if (input[index] == '\r' || input[index] == '\n' || input[index] == '\0') {
            return RELAY_COMMAND_MULTILINE;
        }
    }

    const size_t command_length = end - start;
    memcpy(output, input + start, command_length);
    output[command_length] = '\0';
    return RELAY_COMMAND_READY;
}

RelayUartRoute RelayRouter::classifyUartLine(const char* line) {
    if (line && (strncmp(line, "ACK ", 4) == 0 ||
                 strncmp(line, "NACK ", 5) == 0)) {
        return RELAY_UART_COMMAND_RESPONSE;
    }
    return RELAY_UART_TELEMETRY;
}
