#ifndef GNC_ONLY_BENCH_CASES_H
#define GNC_ONLY_BENCH_CASES_H

#include <unity.h>
#include <Arduino.h>

#include "../src/algorithms/kalman.cpp"
#include "../src/algorithms/pid.cpp"
#include "../src/flight_fsm.cpp"
#include "../src/command_line_buffer.h"
#include "../src/command_processor.cpp"
#include "../src/sensor_validity.cpp"
#include "sensor_validity_cases.h"
#include "../src/main.cpp"

void setUp() {}
void tearDown() {}

static void resetBenchHarness(FakeSensorBus& bus) {
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

void test_gnc_only_valid_sensor_keeps_tvc_and_no_recovery_output() {
    FakeSensorBus bus;
    resetBenchHarness(bus);
    Serial2.input = "arm\nset_servo:91,89\n";
    loop();

    TEST_ASSERT_TRUE(sensors.controlReady());
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(COMMAND_ARMED, commandProcessor.state());
    TEST_ASSERT_EQUAL(91, servoPitch.last_angle);
    TEST_ASSERT_EQUAL(89, servoRoll.last_angle);
    TEST_ASSERT_EQUAL(FS_IDLE, fsm.getState());
    TEST_ASSERT_EQUAL(-1, servoRecovery.pin);
    TEST_ASSERT_EQUAL(0, servoRecovery.writes);
    Serial2.input = "auto_on\n";
    loop();
    TEST_ASSERT_TRUE(auto_mode);
    TEST_ASSERT_TRUE(commandProcessor.autoEnabled());
    TEST_ASSERT_TRUE(servoPitch.writes > 2);
    TEST_ASSERT_TRUE(servoRoll.writes > 2);
    TEST_ASSERT_EQUAL(0, servoRecovery.writes);
}

void test_gnc_only_deploy_command_is_rejected_without_recovery_state_or_output() {
    FakeSensorBus bus;
    resetBenchHarness(bus);
    Serial2.input = "arm\nauto_on\n";
    loop();
    Serial2.output.clear();
    Serial2.input = "deploy_chute\n";
    loop();

    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(),
                                     "NACK recovery_disabled deploy_chute\n"));
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());
    TEST_ASSERT_TRUE(auto_mode);
    TEST_ASSERT_EQUAL(0, servoRecovery.writes);
}

void test_gnc_only_sensor_fault_neutralizes_tvc_and_rejects_control() {
    FakeSensorBus bus;
    resetBenchHarness(bus);
    Serial.input = "arm\nauto_on\n";
    loop();
    bus.present[0x68] = false;
    Serial2.output.clear();
    Serial2.input = "arm\nauto_on\nset_servo:91,91\ndeploy_chute\n";
    loop();

    TEST_ASSERT_TRUE(sensors.faultLatched());
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_EQUAL(90, servoRoll.last_angle);
    TEST_ASSERT_EQUAL(0, servoRecovery.writes);
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(),
                                     "NACK sensor_invalid arm\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(),
                                     "NACK sensor_invalid auto_on\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(),
                                     "NACK sensor_invalid set_servo\n"));
    TEST_ASSERT_NOT_NULL(std::strstr(Serial2.output.c_str(),
                                     "NACK recovery_disabled deploy_chute\n"));
}

void test_gnc_only_estop_reset_rearms_tvc_without_recovery_fsm() {
    FakeSensorBus bus;
    resetBenchHarness(bus);
    Serial2.input = "arm\nauto_on\n";
    loop();
    Serial.input = "estop\nreset\n";
    loop();

    TEST_ASSERT_EQUAL(COMMAND_IDLE, commandProcessor.state());
    TEST_ASSERT_FALSE(auto_mode);
    TEST_ASSERT_EQUAL(FS_IDLE, fsm.getState());
    TEST_ASSERT_EQUAL(90, servoPitch.last_angle);
    TEST_ASSERT_EQUAL(90, servoRoll.last_angle);
    TEST_ASSERT_EQUAL(0, servoRecovery.writes);

    bus.wordBE(0x68, 0x3F, 32767);
    Serial2.input = "arm\nauto_on\n";
    loop();
    TEST_ASSERT_TRUE(auto_mode);
    TEST_ASSERT_EQUAL(FS_IDLE, fsm.getState());
    TEST_ASSERT_EQUAL(0, servoRecovery.writes);
}

#endif
