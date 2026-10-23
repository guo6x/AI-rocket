#ifndef MAIN_LOOP_CASES_H
#define MAIN_LOOP_CASES_H

// Build the actual production orchestration against native-only boundary fakes.
// This verifies software write intent, never physical movement/timing/electrics.
#include "../src/algorithms/pid.cpp"
#include "../src/main.cpp"

static void resetFlightHarness(FakeSensorBus& bus) {
    Wire = FakeWire();
    Wire.bus = &bus;
    sensorBus = WireSensorBus();
    sensors = SensorValidity();
    sensorSample = SensorSample();
    fsm.reset();
    commandProcessor.resetForTest();
    auto_mode = false;
    kfPitch.init();
    kfRoll.init();
    pidPitch.reset();
    pidRoll.reset();
    Serial.input.clear(); Serial.output.clear();
    Serial2.input.clear(); Serial2.output.clear();
    serialCommandBuffer = CommandLineBuffer();
    serial2CommandBuffer = CommandLineBuffer();
    servoPitch = Servo(); servoRoll = Servo(); servoRecovery = Servo();
    fake_millis = 1000;
    setup();
    Serial.output.clear(); Serial2.output.clear();
}

void test_actual_wire_adapter_rejects_nack_short_and_negative_reads() {
    FakeSensorBus bus;
    WireSensorBus adapter;
    uint8_t output[14];
    Wire = FakeWire(); Wire.bus = &bus;
    TEST_ASSERT_EQUAL(14, adapter.readRegisters(0x68, 0x3B, output, 14));
    Wire.pointer_nack = 2;
    TEST_ASSERT_EQUAL(0, adapter.readRegisters(0x68, 0x3B, output, 14));
    Wire.pointer_nack = 0;
    Wire.short_buffer = true;
    TEST_ASSERT_NOT_EQUAL(14, adapter.readRegisters(0x68, 0x3B, output, 14));
    Wire.short_buffer = false;
    Wire.negative_read_index = 3;
    TEST_ASSERT_EQUAL(3, adapter.readRegisters(0x68, 0x3B, output, 14));
    Wire.negative_read_index = -1;
    Wire.write_failure = 1;
    TEST_ASSERT_FALSE(adapter.writeRegister(0x68, 0x1C, 0));
    TEST_ASSERT_EQUAL(0, adapter.readRegisters(0x68, 0x3B, output, 14));
    Wire = FakeWire();
}

void test_actual_wire_adapter_enforces_sample_io_budget() {
    FakeSensorBus bus;
    WireSensorBus adapter;
    uint8_t output[14];
    Wire = FakeWire(); Wire.bus = &bus;
    fake_millis = 1;
    adapter.beginSample();
    fake_millis += WireSensorBus::SAMPLE_IO_BUDGET_MS;
    const unsigned reads = bus.reads;
    TEST_ASSERT_EQUAL(0, adapter.readRegisters(0x68, 0x3B, output, 14));
    TEST_ASSERT_TRUE(adapter.sampleBudgetExpired());
    TEST_ASSERT_EQUAL(reads, bus.reads);
    fake_millis = ~0UL - 10;
    adapter.beginSample();
    fake_millis = 20;
    TEST_ASSERT_TRUE(adapter.sampleBudgetExpired());
    Wire = FakeWire();
}

void test_actual_loop_gates_commands_before_first_and_lost_sample() {
    FakeSensorBus bus;
    resetFlightHarness(bus);
    TEST_ASSERT_FALSE(sensors.controlReady());
    Serial2.input = "arm\nauto_on\n";
    loop(); // first valid cycle precedes dispatch and can explicitly arm AUTO
    TEST_ASSERT_TRUE(auto_mode);
    TEST_ASSERT_TRUE(commandProcessor.autoEnabled());
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(), "ACK arm\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(), "ACK auto_on\n"));

    bus.short_address = 0x68; bus.short_register = 0x3B; bus.short_length = 13;
    Serial2.input = "auto_on\nset_servo:91,91\n";
    Serial2.output.clear();
    loop();
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_FALSE(commandProcessor.autoEnabled());
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_EQUAL(90, servoRoll.last_angle);
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(), "NACK sensor_invalid auto_on\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(), "NACK sensor_invalid set_servo\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(), "\"sensor_valid\":0"));
    TEST_ASSERT_NULL(std::strstr(Serial2.output.c_str(), "\"alt\":"));
    TEST_ASSERT_NULL(std::strstr(Serial2.output.c_str(), "\"pitch_raw\":"));
}

void test_actual_loop_budget_exhaustion_still_services_estop() {
    FakeSensorBus bus;
    resetFlightHarness(bus);
    Serial2.input = "arm\nauto_on\n";
    loop();
    TEST_ASSERT_TRUE(auto_mode);
    Wire.read_advance_ms = 10;
    const unsigned reads = bus.reads;
    Serial.input = "estop\n";
    loop();
    // Three synthetic 10ms reads exhaust the25ms admission budget. This tests
    // scheduling and fault handling only, not any target's physical IO latency.
    TEST_ASSERT_LESS_OR_EQUAL(3, bus.reads - reads);
    TEST_ASSERT_TRUE(sensorBus.sampleBudgetExpired());
    TEST_ASSERT_TRUE(sensors.faultLatched());
    TEST_ASSERT_TRUE(commandProcessor.estopLatched());
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_NOT_NULL(std::strstr(Serial.output.c_str(), "ACK estop\n"));
}

void test_actual_loop_fault_skips_kalman_pid_and_recovery_fsm() {
    FakeSensorBus bus;
    resetFlightHarness(bus);
    Serial.input = "arm\nauto_on\n";
    loop();
    const float filtered_before = kfPitch.update(20, 10, 0.01f);
    pidPitch.compute(10, 0.01f);
    TEST_ASSERT_TRUE(pidPitch.getLastOutput() != 0);
    drive_to_powered(fsm, 1000);
    fake_millis = 20000; // an FSM update here would fire backup recovery
    bus.present[0x76] = false;
    const unsigned recovery_writes = servoRecovery.writes;
    loop();
    TEST_ASSERT_EQUAL_FLOAT(filtered_before, kfPitch.getAngle());
    TEST_ASSERT_EQUAL_FLOAT(0, pidPitch.getLastOutput());
    TEST_ASSERT_EQUAL(FS_POWERED, fsm.getState());
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(recovery_writes, servoRecovery.writes);
    TEST_ASSERT_FALSE(auto_mode);
}

void test_actual_loop_reset_and_reconnected_sensor_cannot_resume_auto() {
    FakeSensorBus bus;
    resetFlightHarness(bus);
    Serial.input = "arm\nauto_on\n";
    loop();
    bus.present[0x68] = false;
    Serial2.input = "estop\nreset\narm\nauto_on\n";
    loop();
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, commandProcessor.state());
    TEST_ASSERT_TRUE(sensors.faultLatched());
    bus.present[0x68] = true;
    Serial.input = "arm\nset_servo:91,91\n";
    loop();
    TEST_ASSERT_FALSE(sensors.controlReady());
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, commandProcessor.state());
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_NOT_NULL(std::strstr(Serial.output.c_str(), "NACK sensor_invalid arm\n"));
}

void test_actual_loop_estop_reset_and_emergency_deploy_survive_sensor_fault() {
    FakeSensorBus bus;
    resetFlightHarness(bus);
    bus.present[0x68] = false;
    Serial.input = "estop\ndeploy_chute\nreset\n";
    loop();
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(0, servoRecovery.last_angle); // captured software intent only
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_EQUAL(90, servoRoll.last_angle);
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_NOT_NULL(std::strstr(Serial.output.c_str(), "ACK estop\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial.output.c_str(), "ACK deploy_chute\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial.output.c_str(), "ACK reset\n"));
}

void test_actual_loop_failed_init_never_reads_or_moves_with_control_commands() {
    FakeSensorBus bus;
    bus.registers[0x68][0x75] = 0xFF;
    resetFlightHarness(bus);
    const unsigned read_count = bus.reads;
    Serial.input = "arm\nauto_on\nset_servo:91,91\n";
    loop();
    TEST_ASSERT_EQUAL(read_count, bus.reads);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, commandProcessor.state());
    TEST_ASSERT_EQUAL_FLOAT(0, kfPitch.getAngle());
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_EQUAL(90, servoRoll.last_angle);
    TEST_ASSERT_EQUAL(90, servoRecovery.last_angle);
    FakeSensorBus no_bmp;
    no_bmp.present[0x76] = false;
    resetFlightHarness(no_bmp);
    const unsigned bmp_init_reads = no_bmp.reads;
    Serial2.input = "arm\nauto_on\n";
    loop();
    TEST_ASSERT_EQUAL(bmp_init_reads, no_bmp.reads);
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
}

#endif
