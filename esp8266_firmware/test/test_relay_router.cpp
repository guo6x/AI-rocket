#include <unity.h>

#include "../src/relay_router.h"
#include "../src/relay_router.cpp"

void setUp() {}
void tearDown() {}

void test_valid_plaintext_command_is_forwarded() {
    const uint8_t input[] = " set_servo:90,90 ";
    char output[RelayRouter::MAX_COMMAND_BYTES + 1];
    TEST_ASSERT_EQUAL(RELAY_COMMAND_READY,
                      RelayRouter::validateCommandDatagram(
                          input, sizeof(input) - 1, output, sizeof(output)));
    TEST_ASSERT_EQUAL_STRING("set_servo:90,90", output);
}

void test_empty_overlong_and_multiline_are_rejected() {
    char output[RelayRouter::MAX_COMMAND_BYTES + 1];
    const uint8_t empty[] = "   ";
    TEST_ASSERT_EQUAL(RELAY_COMMAND_EMPTY,
                      RelayRouter::validateCommandDatagram(
                          empty, sizeof(empty) - 1, output, sizeof(output)));

    uint8_t overlong[RelayRouter::MAX_COMMAND_BYTES + 1];
    for (size_t i = 0; i < sizeof(overlong); ++i) overlong[i] = 'x';
    TEST_ASSERT_EQUAL(RELAY_COMMAND_OVERLONG,
                      RelayRouter::validateCommandDatagram(
                          overlong, sizeof(overlong), output, sizeof(output)));

    const uint8_t multiline[] = "arm\nestop";
    TEST_ASSERT_EQUAL(RELAY_COMMAND_MULTILINE,
                      RelayRouter::validateCommandDatagram(
                          multiline, sizeof(multiline) - 1, output, sizeof(output)));
}

void test_ack_nack_return_to_command_client() {
    TEST_ASSERT_EQUAL(RELAY_UART_COMMAND_RESPONSE,
                      RelayRouter::classifyUartLine("ACK arm"));
    TEST_ASSERT_EQUAL(RELAY_UART_COMMAND_RESPONSE,
                      RelayRouter::classifyUartLine("NACK invalid_state auto_on"));
    TEST_ASSERT_EQUAL(RELAY_UART_TELEMETRY,
                      RelayRouter::classifyUartLine("{\"time\":1}"));
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_valid_plaintext_command_is_forwarded);
    RUN_TEST(test_empty_overlong_and_multiline_are_rejected);
    RUN_TEST(test_ack_nack_return_to_command_client);
    return UNITY_END();
}
