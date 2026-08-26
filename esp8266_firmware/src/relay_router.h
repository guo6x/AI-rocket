#ifndef RELAY_ROUTER_H
#define RELAY_ROUTER_H

#include <stddef.h>
#include <stdint.h>

enum RelayCommandResult {
    RELAY_COMMAND_READY,
    RELAY_COMMAND_EMPTY,
    RELAY_COMMAND_OVERLONG,
    RELAY_COMMAND_MULTILINE
};

enum RelayUartRoute {
    RELAY_UART_TELEMETRY,
    RELAY_UART_COMMAND_RESPONSE
};

class RelayRouter {
public:
    static const size_t MAX_COMMAND_BYTES = 128;

    static RelayCommandResult validateCommandDatagram(
        const uint8_t* input, size_t length, char* output, size_t output_size);
    static RelayUartRoute classifyUartLine(const char* line);
};

#endif
