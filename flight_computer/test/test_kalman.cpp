#include <unity.h>
#include "../src/algorithms/kalman.h"
#include "../src/algorithms/kalman.cpp" // 直接包含以方便 native 编译，或者在 platformio.ini 中配置
#include "../src/flight_fsm.h"
#include "../src/flight_fsm.cpp"
#include "../src/command_line_buffer.h"
#include "../src/command_processor.h"
#include "../src/command_processor.cpp"

void setUp() {}
void tearDown() {}

void test_kalman_initial_state() {
    KalmanFilter kf;
    TEST_ASSERT_EQUAL_FLOAT(0.0f, kf.getAngle());
    TEST_ASSERT_EQUAL_FLOAT(0.0f, kf.getBias());
}

void test_kalman_update() {
    KalmanFilter kf;
    kf.init(0.001f, 0.003f, 0.03f);
    
    // 模拟 1 秒钟，角度从 0 变到 10，角速度为 10
    float angle = kf.update(10.0f, 10.0f, 1.0f);
    
    // 经过一次更新，估计值应该向测量值靠近，但不完全相等（由于滤波）
    TEST_ASSERT_TRUE(angle > 0.0f);
    TEST_ASSERT_TRUE(angle < 15.0f); // 应该在合理范围内
}

void test_kalman_convergence() {
    KalmanFilter kf;
    kf.init(0.001f, 0.003f, 0.03f);
    
    // 多次更新，模拟稳定在 45 度
    float angle = 0;
    for(int i = 0; i < 1000; i++) {
        angle = kf.update(45.0f, 0.0f, 0.01f);
    }

    // 持续稳定测量后应收敛到 45 度附近。
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 45.0f, angle);
}

static void drive_to_powered(FlightStateMachine &fsm, unsigned long start_ms = 1000) {
    fsm.arm(100.0f, start_ms);
    fsm.update(3.0f, 100.0f, start_ms + 10);
    fsm.update(3.0f, 100.0f, start_ms + 20);
    fsm.update(3.0f, 100.0f, start_ms + 30);
}

void test_fsm_requires_three_launch_samples() {
    FlightStateMachine fsm;
    fsm.arm(100.0f, 1000);
    fsm.update(3.0f, 100.0f, 1010);
    fsm.update(3.0f, 100.0f, 1020);
    TEST_ASSERT_EQUAL(FS_ARMED, fsm.getState());
    fsm.update(3.0f, 100.0f, 1030);
    TEST_ASSERT_EQUAL(FS_POWERED, fsm.getState());
    TEST_ASSERT_EQUAL_UINT32(1030, fsm.getLaunchTime());
}

void test_fsm_launch_counter_resets_after_low_sample() {
    FlightStateMachine fsm;
    fsm.arm(0.0f, 0);
    fsm.update(3.0f, 0.0f, 10);
    fsm.update(1.0f, 0.0f, 20);
    fsm.update(3.0f, 0.0f, 30);
    fsm.update(3.0f, 0.0f, 40);
    TEST_ASSERT_EQUAL(FS_ARMED, fsm.getState());
}

void test_fsm_burnout_and_rolling_apogee_window() {
    FlightStateMachine fsm;
    drive_to_powered(fsm);
    fsm.update(1.0f, 0.0f, 1040);  // burnout; also records first coast altitude
    TEST_ASSERT_EQUAL(FS_COAST, fsm.getState());

    const float altitudes[] = {5.0f, 10.0f, 9.0f, 8.0f, 7.0f};
    for (int i = 0; i < 5; i++) {
        fsm.update(1.0f, altitudes[i], 1050 + i * 10);
    }
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());

    fsm.update(1.0f, 6.0f, 1100);
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_DESCENT, fsm.getState());
}

void test_fsm_timer_is_measured_from_detected_launch() {
    FlightStateMachine fsm;
    drive_to_powered(fsm, 2000);
    fsm.update(1.0f, 0.0f, 2030 + 15000);
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());
    fsm.update(1.0f, 0.0f, 2030 + 15001);
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
}

void test_fsm_manual_deploy_and_reset() {
    FlightStateMachine fsm;
    fsm.arm(12.0f, 500);
    fsm.deployChute("TEST");
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_DESCENT, fsm.getState());
    fsm.reset();
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_IDLE, fsm.getState());
}

void test_fsm_disarm_does_not_reload_recovery() {
    FlightStateMachine fsm;
    fsm.arm(12.0f, 500);
    fsm.disarm();
    TEST_ASSERT_EQUAL(FS_IDLE, fsm.getState());
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());

    fsm.deployChute("TEST");
    fsm.disarm();
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_DESCENT, fsm.getState());
}

void test_command_valid_state_sequence_and_actions() {
    CommandProcessor processor;

    CommandDecision pid = processor.process("set_pid:1.0,0.1,0.3");
    TEST_ASSERT_TRUE(pid.accepted());
    TEST_ASSERT_EQUAL(ACTION_SET_PID, pid.action);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 1.0f, pid.kp);

    CommandDecision arm = processor.process("arm");
    TEST_ASSERT_TRUE(arm.accepted());
    TEST_ASSERT_EQUAL(COMMAND_ARMED, processor.state());

    CommandDecision servo = processor.process("set_servo:90,91");
    TEST_ASSERT_TRUE(servo.accepted());
    TEST_ASSERT_EQUAL(90, servo.servo_pitch);
    TEST_ASSERT_EQUAL(91, servo.servo_roll);

    TEST_ASSERT_TRUE(processor.process("auto_on").accepted());
    TEST_ASSERT_TRUE(processor.autoEnabled());
    TEST_ASSERT_TRUE(processor.process("auto_off").accepted());
    TEST_ASSERT_EQUAL(COMMAND_ARMED, processor.state());
    TEST_ASSERT_TRUE(processor.process("auto_off").accepted());
    TEST_ASSERT_TRUE(processor.process("deploy_chute").accepted());
}

void test_estop_reset_never_restores_auto() {
    CommandProcessor processor;
    TEST_ASSERT_TRUE(processor.process("arm").accepted());
    TEST_ASSERT_TRUE(processor.process("auto_on").accepted());
    TEST_ASSERT_TRUE(processor.autoEnabled());

    CommandDecision estop = processor.process("estop");
    TEST_ASSERT_TRUE(estop.accepted());
    TEST_ASSERT_EQUAL(ACTION_ESTOP, estop.action);
    TEST_ASSERT_TRUE(processor.estopLatched());
    TEST_ASSERT_FALSE(processor.autoEnabled());

    CommandDecision reset = processor.process("reset");
    TEST_ASSERT_TRUE(reset.accepted());
    TEST_ASSERT_EQUAL(ACTION_RESET, reset.action);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, processor.state());
    TEST_ASSERT_FALSE(processor.autoEnabled());
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE,
                      processor.process("auto_on").result);
}

void test_estop_is_idempotent_and_gates_unsafe_commands() {
    CommandProcessor processor;
    TEST_ASSERT_TRUE(processor.process("estop").accepted());
    TEST_ASSERT_TRUE(processor.process("estop").accepted());
    TEST_ASSERT_EQUAL(COMMAND_NACK_ESTOP_LATCHED,
                      processor.process("set_servo:90,90").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_ESTOP_LATCHED,
                      processor.process("set_pid:1,0,0.1").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_ESTOP_LATCHED,
                      processor.process("arm").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_servo:bad").result);
    TEST_ASSERT_TRUE(processor.process("deploy_chute").accepted());
}

void test_malformed_unknown_and_extra_arguments_are_atomic() {
    CommandProcessor processor;
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED, processor.process("").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_UNKNOWN, processor.process("launch").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_UNKNOWN, processor.process("set_ser").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_servo:90").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_servo:ninety,90").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_servo:90,90,90").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_pid:1.0,0.1").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_pid:1.0,0.1,nan").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_MALFORMED,
                      processor.process("set_pid:1.0,0.1,0.3,extra").result);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, processor.state());
}

void test_command_ranges_and_state_gates() {
    CommandProcessor processor;
    TEST_ASSERT_EQUAL(COMMAND_NACK_OUT_OF_RANGE,
                      processor.process("set_servo:-1,90").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_OUT_OF_RANGE,
                      processor.process("set_servo:90,181").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_OUT_OF_RANGE,
                      processor.process("set_pid:10.1,0,0").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE,
                      processor.process("set_servo:90,90").result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE,
                      processor.process("arm", true).result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE,
                      processor.process("arm", false, false).result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE,
                      processor.process("reset").result);
}

void test_auto_on_rejects_deployed_recovery_context() {
    CommandProcessor processor;
    TEST_ASSERT_TRUE(processor.process("arm").accepted());

    CommandDecision auto_on = processor.process("auto_on", true);
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE, auto_on.result);
    TEST_ASSERT_EQUAL(ACTION_NONE, auto_on.action);
    TEST_ASSERT_EQUAL(COMMAND_ARMED, processor.state());
    TEST_ASSERT_FALSE(processor.autoEnabled());
}

void test_automatic_recovery_transition_prevents_auto_reenable() {
    FlightStateMachine fsm;
    CommandProcessor processor;
    TEST_ASSERT_TRUE(processor.process(
        "arm", fsm.isChuteDeployed(), fsm.getState() == FS_IDLE).accepted());
    fsm.arm(0.0f, 1000);
    TEST_ASSERT_TRUE(processor.process("auto_on").accepted());

    drive_to_powered(fsm, 1010);
    fsm.update(1.0f, 0.0f, 1040 + 15001);
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    processor.disableAutoForSafety();

    CommandDecision auto_on = processor.process(
        "auto_on", fsm.isChuteDeployed(), fsm.getState() == FS_IDLE);
    TEST_ASSERT_EQUAL(COMMAND_NACK_INVALID_STATE, auto_on.result);
    TEST_ASSERT_EQUAL(COMMAND_ARMED, processor.state());
    TEST_ASSERT_FALSE(processor.autoEnabled());
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
}

static CommandLineEvent feed(CommandLineBuffer& buffer, const char* text) {
    CommandLineEvent event = COMMAND_LINE_NONE;
    while (*text) event = buffer.push(*text++);
    return event;
}

void test_serial_and_serial2_buffers_are_isolated() {
    CommandLineBuffer serial;
    CommandLineBuffer serial2;

    TEST_ASSERT_EQUAL(COMMAND_LINE_NONE, feed(serial, "set_ser"));
    TEST_ASSERT_EQUAL(COMMAND_LINE_READY, feed(serial2, "estop\n"));
    TEST_ASSERT_EQUAL_STRING("estop", serial2.line());
    TEST_ASSERT_EQUAL(COMMAND_LINE_READY, feed(serial, "vo:90,90\n"));
    TEST_ASSERT_EQUAL_STRING("set_servo:90,90", serial.line());
}

void test_overlong_line_is_discarded_until_clean_boundary() {
    CommandLineBuffer buffer;
    for (size_t i = 0; i < CommandLineBuffer::MAX_BYTES + 1; ++i) {
        TEST_ASSERT_EQUAL(COMMAND_LINE_NONE, buffer.push('x'));
    }
    TEST_ASSERT_TRUE(buffer.discarding());
    TEST_ASSERT_EQUAL(COMMAND_LINE_OVERLONG, buffer.push('\n'));
    TEST_ASSERT_FALSE(buffer.discarding());
    TEST_ASSERT_EQUAL(COMMAND_LINE_READY, feed(buffer, "arm\n"));
    TEST_ASSERT_EQUAL_STRING("arm", buffer.line());
}

void test_embedded_nul_discards_entire_line() {
    CommandLineBuffer buffer;
    TEST_ASSERT_EQUAL(COMMAND_LINE_NONE, feed(buffer, "estop"));
    TEST_ASSERT_EQUAL(COMMAND_LINE_NONE, buffer.push('\0'));
    TEST_ASSERT_EQUAL(COMMAND_LINE_NONE, feed(buffer, "junk"));
    TEST_ASSERT_EQUAL(COMMAND_LINE_MALFORMED, buffer.push('\n'));
    TEST_ASSERT_EQUAL(COMMAND_LINE_READY, feed(buffer, "arm\n"));
    TEST_ASSERT_EQUAL_STRING("arm", buffer.line());
}

void test_ack_nack_reason_vocabulary() {
    TEST_ASSERT_EQUAL_STRING("accepted", CommandProcessor::resultText(COMMAND_ACK));
    TEST_ASSERT_EQUAL_STRING("malformed",
                             CommandProcessor::resultText(COMMAND_NACK_MALFORMED));
    TEST_ASSERT_EQUAL_STRING("invalid_state",
                             CommandProcessor::resultText(COMMAND_NACK_INVALID_STATE));
    TEST_ASSERT_EQUAL_STRING("out_of_range",
                             CommandProcessor::resultText(COMMAND_NACK_OUT_OF_RANGE));
    TEST_ASSERT_EQUAL_STRING("estop_latched",
                             CommandProcessor::resultText(COMMAND_NACK_ESTOP_LATCHED));
    TEST_ASSERT_EQUAL_STRING("unknown_command",
                             CommandProcessor::resultText(COMMAND_NACK_UNKNOWN));
}

void test_line_buffer_to_canonical_processor_end_to_end() {
    CommandLineBuffer wifi_uart;
    CommandProcessor processor;
    TEST_ASSERT_EQUAL(COMMAND_LINE_READY, feed(wifi_uart, "arm\n"));
    CommandDecision decision = processor.process(wifi_uart.line());
    TEST_ASSERT_TRUE(decision.accepted());
    TEST_ASSERT_EQUAL_STRING("arm", decision.command_name);
    TEST_ASSERT_EQUAL_STRING("accepted",
                             CommandProcessor::resultText(decision.result));
    TEST_ASSERT_EQUAL(COMMAND_ARMED, processor.state());
}

int main(int argc, char **argv) {
    UNITY_BEGIN();
    RUN_TEST(test_kalman_initial_state);
    RUN_TEST(test_kalman_update);
    RUN_TEST(test_kalman_convergence);
    RUN_TEST(test_fsm_requires_three_launch_samples);
    RUN_TEST(test_fsm_launch_counter_resets_after_low_sample);
    RUN_TEST(test_fsm_burnout_and_rolling_apogee_window);
    RUN_TEST(test_fsm_timer_is_measured_from_detected_launch);
    RUN_TEST(test_fsm_manual_deploy_and_reset);
    RUN_TEST(test_fsm_disarm_does_not_reload_recovery);
    RUN_TEST(test_command_valid_state_sequence_and_actions);
    RUN_TEST(test_estop_reset_never_restores_auto);
    RUN_TEST(test_estop_is_idempotent_and_gates_unsafe_commands);
    RUN_TEST(test_malformed_unknown_and_extra_arguments_are_atomic);
    RUN_TEST(test_command_ranges_and_state_gates);
    RUN_TEST(test_auto_on_rejects_deployed_recovery_context);
    RUN_TEST(test_automatic_recovery_transition_prevents_auto_reenable);
    RUN_TEST(test_serial_and_serial2_buffers_are_isolated);
    RUN_TEST(test_overlong_line_is_discarded_until_clean_boundary);
    RUN_TEST(test_embedded_nul_discards_entire_line);
    RUN_TEST(test_ack_nack_reason_vocabulary);
    RUN_TEST(test_line_buffer_to_canonical_processor_end_to_end);
    return UNITY_END();
}
