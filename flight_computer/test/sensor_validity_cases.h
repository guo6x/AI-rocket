#ifndef SENSOR_VALIDITY_CASES_H
#define SENSOR_VALIDITY_CASES_H

#include <cmath>
#include <cstring>
#include <limits>
#include <initializer_list>

// Register-level fake only; none of these tests opens a bus or an actuator.
class FakeSensorBus : public SensorBus {
public:
    uint8_t registers[128][256];
    bool present[128];
    int short_address, short_register, short_length;
    int failed_write_register, corrupt_register;
    unsigned reads, writes, bmp_busy_reads;

    FakeSensorBus() : short_address(-1), short_register(-1), short_length(0),
                      failed_write_register(-1), corrupt_register(-1),
                      reads(0), writes(0), bmp_busy_reads(0) {
        std::memset(registers, 0, sizeof(registers));
        std::memset(present, 0, sizeof(present));
        present[0x68] = true;
        present[0x76] = true;
        registers[0x68][0x75] = 0x71;
        registers[0x76][0xD0] = 0x58;
        wordBE(0x68, 0x3F, 16384); // stationary +1 g on Z
        const int coefficients[] = {27504, 26435, -1000, 36477, -10685,
                                   3024, 2855, 140, -7, 15500, -14600, 6000};
        for (unsigned i = 0; i < 12; ++i) {
            const uint16_t value = static_cast<uint16_t>(coefficients[i]);
            registers[0x76][0x88 + i * 2] = value & 0xFF;
            registers[0x76][0x89 + i * 2] = value >> 8;
        }
        raw20(0x76, 0xF7, 415148);
        raw20(0x76, 0xFA, 519888);
    }

    void wordBE(uint8_t address, uint8_t reg, int value) {
        const uint16_t bits = static_cast<uint16_t>(value);
        registers[address][reg] = bits >> 8;
        registers[address][reg + 1] = bits & 0xFF;
    }

    void raw20(uint8_t address, uint8_t reg, uint32_t value) {
        registers[address][reg] = value >> 12;
        registers[address][reg + 1] = value >> 4;
        registers[address][reg + 2] = (value & 0x0F) << 4;
    }

    void moveDevice(uint8_t from, uint8_t to) {
        std::memcpy(registers[to], registers[from], sizeof(registers[to]));
        present[to] = true;
        present[from] = false;
    }

    bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) override {
        ++writes;
        if (!present[address] || reg == failed_write_register) return false;
        registers[address][reg] = value;
        return true;
    }

    size_t readRegisters(uint8_t address, uint8_t reg, uint8_t* output,
                         size_t length) override {
        ++reads;
        if (!present[address]) return 0;
        if ((address == 0x76 || address == 0x77) && reg == 0xF3 && bmp_busy_reads) {
            --bmp_busy_reads;
            output[0] = 0x09;
            return 1;
        }
        if (address == short_address && reg == short_register)
            length = static_cast<size_t>(short_length);
        std::memcpy(output, registers[address] + reg, length);
        if (reg == corrupt_register && length) output[0] ^= 0x08;
        return length;
    }

    void waitMilliseconds(uint16_t) override {}
};

void test_gy91_supported_identities_and_addresses() {
    const uint8_t ids[] = {0x70, 0x71};
    for (uint8_t id : ids) {
        for (uint8_t imu_address : {0x68, 0x69}) {
            for (uint8_t bmp_address : {0x76, 0x77}) {
                FakeSensorBus bus;
                bus.registers[0x68][0x75] = id;
                if (imu_address != 0x68) bus.moveDevice(0x68, imu_address);
                if (bmp_address != 0x76) bus.moveDevice(0x76, bmp_address);
                SensorValidity sensors;
                SensorSample sample;
                TEST_ASSERT_TRUE(sensors.begin(bus));
                TEST_ASSERT_FALSE(sensors.controlReady());
                TEST_ASSERT_EQUAL_HEX8(id, sensors.imuIdentity());
                TEST_ASSERT_EQUAL_HEX8(imu_address, sensors.imuAddress());
                TEST_ASSERT_EQUAL_HEX8(bmp_address, sensors.bmpAddress());
                TEST_ASSERT_EQUAL_HEX8(0x58, sensors.bmpIdentity());
                TEST_ASSERT_TRUE(sensors.read(bus, 1234, sample));
                TEST_ASSERT_TRUE(sample.valid);
                TEST_ASSERT_TRUE(sensors.controlReady());
                TEST_ASSERT_EQUAL_UINT32(1234, sample.time_ms);
            }
        }
    }
}

void test_gy91_unknown_and_missing_identity_fail_closed() {
    const uint8_t unknowns[] = {0x00, 0xFF, 0x68, 0x73};
    for (uint8_t id : unknowns) {
        FakeSensorBus bus;
        bus.registers[0x68][0x75] = id;
        SensorValidity sensors;
        TEST_ASSERT_FALSE(sensors.begin(bus));
        TEST_ASSERT_EQUAL(SENSOR_IMU_IDENTITY, sensors.fault());
        TEST_ASSERT_EQUAL_HEX8(id, sensors.imuIdentity());
        TEST_ASSERT_FALSE(sensors.controlReady());
        TEST_ASSERT_EQUAL(0, bus.writes);
    }
    FakeSensorBus bus;
    bus.present[0x68] = false;
    SensorValidity sensors;
    TEST_ASSERT_FALSE(sensors.begin(bus));
    TEST_ASSERT_EQUAL(SENSOR_IMU_MISSING, sensors.fault());
    SensorSample sample;
    const unsigned reads = bus.reads;
    TEST_ASSERT_FALSE(sensors.read(bus, 1, sample));
    TEST_ASSERT_EQUAL(reads, bus.reads); // failed init never reads BMP later
    TEST_ASSERT_TRUE(std::isnan(sample.altitude_m));
}

void test_gy91_checked_writes_and_scale_readback() {
    const int config_registers[] = {0x6B, 0x6C, 0x1B, 0x1C};
    for (int reg : config_registers) {
        FakeSensorBus write_bus;
        write_bus.failed_write_register = reg;
        SensorValidity write_sensor;
        TEST_ASSERT_FALSE(write_sensor.begin(write_bus));
        TEST_ASSERT_EQUAL(SENSOR_CONFIG_WRITE, write_sensor.fault());
        FakeSensorBus readback_bus;
        readback_bus.corrupt_register = reg;
        SensorValidity readback_sensor;
        TEST_ASSERT_FALSE(readback_sensor.begin(readback_bus));
        TEST_ASSERT_EQUAL(SENSOR_CONFIG_READBACK, readback_sensor.fault());
    }
}

void test_gy91_every_short_imu_read_is_invalid() {
    for (int length = 0; length < 14; ++length) {
        FakeSensorBus bus;
        SensorValidity sensors;
        SensorSample sample;
        TEST_ASSERT_TRUE(sensors.begin(bus));
        bus.short_address = 0x68;
        bus.short_register = 0x3B;
        bus.short_length = length;
        TEST_ASSERT_FALSE(sensors.read(bus, 5, sample));
        TEST_ASSERT_EQUAL(SENSOR_IMU_READ, sensors.fault());
        TEST_ASSERT_FALSE(sample.valid);
        TEST_ASSERT_TRUE(std::isnan(sample.ax));
        TEST_ASSERT_FALSE(sensors.controlReady());
    }
}

void test_gy91_signed_decode_and_reference_barometer_sample() {
    FakeSensorBus bus;
    bus.wordBE(0x68, 0x3B, -8192);
    bus.wordBE(0x68, 0x43, -131);
    bus.wordBE(0x68, 0x47, 262);
    SensorValidity sensors;
    SensorSample sample;
    TEST_ASSERT_TRUE(sensors.begin(bus));
    TEST_ASSERT_TRUE(sensors.read(bus, 200, sample));
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, -0.5f, sample.ax);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, -1.0f, sample.gx);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 2.0f, sample.gz);
    // BMP280 datasheet compensation example: adc_T=519888, adc_P=415148.
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 25.08f, sample.temperature_c);
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 100653.25f, sample.pressure_pa);
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 56.1f, sample.altitude_m);
}

void test_gy91_invalid_raw_samples_do_not_become_zero_attitude() {
    const uint8_t invalid_fills[] = {0x00, 0xFF};
    for (uint8_t value : invalid_fills) {
        FakeSensorBus bus;
        SensorValidity sensors;
        SensorSample sample;
        TEST_ASSERT_TRUE(sensors.begin(bus));
        std::memset(bus.registers[0x68] + 0x3B, value, 14);
        TEST_ASSERT_FALSE(sensors.read(bus, 5, sample));
        TEST_ASSERT_EQUAL(SENSOR_IMU_SAMPLE, sensors.fault());
        TEST_ASSERT_FALSE(sample.valid);
        TEST_ASSERT_TRUE(std::isnan(sample.az));
    }
}

void test_gy91_bmp_identity_calibration_and_config_failures() {
    FakeSensorBus missing;
    missing.present[0x76] = false;
    SensorValidity no_bmp;
    TEST_ASSERT_FALSE(no_bmp.begin(missing));
    TEST_ASSERT_EQUAL(SENSOR_BMP_MISSING, no_bmp.fault());

    FakeSensorBus wrong;
    wrong.registers[0x76][0xD0] = 0x60; // BME280 is not silently called BMP280
    SensorValidity wrong_bmp;
    TEST_ASSERT_FALSE(wrong_bmp.begin(wrong));
    TEST_ASSERT_EQUAL(SENSOR_BMP_IDENTITY, wrong_bmp.fault());

    for (int length = 0; length < 24; ++length) {
        FakeSensorBus bus;
        bus.short_address = 0x76;
        bus.short_register = 0x88;
        bus.short_length = length;
        SensorValidity sensors;
        TEST_ASSERT_FALSE(sensors.begin(bus));
        TEST_ASSERT_EQUAL(SENSOR_BMP_CALIBRATION, sensors.fault());
    }
    FakeSensorBus zero_calib;
    zero_calib.registers[0x76][0x8E] = 0;
    zero_calib.registers[0x76][0x8F] = 0;
    SensorValidity invalid_calib;
    TEST_ASSERT_FALSE(invalid_calib.begin(zero_calib));
    TEST_ASSERT_EQUAL(SENSOR_BMP_CALIBRATION, invalid_calib.fault());

    for (int reg : {0xF4, 0xF5}) {
        FakeSensorBus write_bus;
        write_bus.failed_write_register = reg;
        SensorValidity write_sensor;
        TEST_ASSERT_FALSE(write_sensor.begin(write_bus));
        TEST_ASSERT_EQUAL(SENSOR_CONFIG_WRITE, write_sensor.fault());
        FakeSensorBus readback_bus;
        readback_bus.corrupt_register = reg;
        SensorValidity readback_sensor;
        TEST_ASSERT_FALSE(readback_sensor.begin(readback_bus));
        TEST_ASSERT_EQUAL(SENSOR_CONFIG_READBACK, readback_sensor.fault());
    }
}

void test_gy91_bmp_waits_for_sleep_and_calibration_copy() {
    FakeSensorBus finishing;
    finishing.bmp_busy_reads = 60;
    SensorValidity good;
    TEST_ASSERT_TRUE(good.begin(finishing));
    TEST_ASSERT_EQUAL(0, finishing.bmp_busy_reads);
    FakeSensorBus stuck;
    stuck.bmp_busy_reads = 101;
    SensorValidity timed_out;
    TEST_ASSERT_FALSE(timed_out.begin(stuck));
    TEST_ASSERT_EQUAL(SENSOR_BMP_STATUS, timed_out.fault());
    FakeSensorBus nack;
    nack.short_address = 0x76;
    nack.short_register = 0xF3;
    nack.short_length = 0;
    SensorValidity status_read;
    TEST_ASSERT_FALSE(status_read.begin(nack));
    TEST_ASSERT_EQUAL(SENSOR_BMP_STATUS, status_read.fault());
}

void test_gy91_bmp_short_and_disabled_samples_fail_closed() {
    for (int length = 0; length < 6; ++length) {
        FakeSensorBus bus;
        SensorValidity sensors;
        SensorSample sample;
        TEST_ASSERT_TRUE(sensors.begin(bus));
        bus.short_address = 0x76;
        bus.short_register = 0xF7;
        bus.short_length = length;
        TEST_ASSERT_FALSE(sensors.read(bus, 1, sample));
        TEST_ASSERT_EQUAL(SENSOR_BMP_READ, sensors.fault());
        TEST_ASSERT_TRUE(std::isnan(sample.altitude_m));
    }
    for (int reg : {0xF7, 0xFA}) {
        FakeSensorBus bus;
        SensorValidity sensors;
        SensorSample sample;
        TEST_ASSERT_TRUE(sensors.begin(bus));
        bus.raw20(0x76, reg, 0x80000); // datasheet skipped-measurement sentinel
        TEST_ASSERT_FALSE(sensors.read(bus, 2, sample));
        TEST_ASSERT_EQUAL(SENSOR_BMP_SAMPLE, sensors.fault());
    }
}

void test_gy91_nonfinite_and_out_of_range_values_fail_closed() {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    TEST_ASSERT_FALSE(SensorValidity::barometerValuesValid(nan, 25, 0));
    TEST_ASSERT_FALSE(SensorValidity::barometerValuesValid(100000, inf, 0));
    TEST_ASSERT_FALSE(SensorValidity::barometerValuesValid(100000, 25, nan));
    TEST_ASSERT_FALSE(SensorValidity::barometerValuesValid(0, 25, 0));
    TEST_ASSERT_FALSE(SensorValidity::barometerValuesValid(110001, 25, 0));
    TEST_ASSERT_FALSE(SensorValidity::barometerValuesValid(100000, -41, 0));
    TEST_ASSERT_TRUE(SensorValidity::barometerValuesValid(100000, 25, 0));
    FakeSensorBus bus;
    SensorValidity sensors;
    SensorSample sample;
    TEST_ASSERT_TRUE(sensors.begin(bus));
    bus.raw20(0x76, 0xF7, 0);
    TEST_ASSERT_FALSE(sensors.read(bus, 2, sample));
    TEST_ASSERT_FALSE(sensors.controlReady());
}

void test_gy91_runtime_identity_or_scale_change_latches() {
    for (int reg : {0x75, 0x1B, 0x1C, 0x6B, 0x6C}) {
        FakeSensorBus bus;
        SensorValidity sensors;
        SensorSample sample;
        TEST_ASSERT_TRUE(sensors.begin(bus));
        TEST_ASSERT_TRUE(sensors.read(bus, 1, sample));
        bus.registers[0x68][reg] ^= 0x08;
        TEST_ASSERT_FALSE(sensors.read(bus, 2, sample));
        TEST_ASSERT_FALSE(sensors.controlReady());
        TEST_ASSERT_TRUE(sensors.faultLatched());
        bus.registers[0x68][reg] ^= 0x08;
        const unsigned reads = bus.reads;
        TEST_ASSERT_FALSE(sensors.read(bus, 3, sample));
        TEST_ASSERT_FALSE(sensors.begin(bus)); // no soft reset/reinit bypass
        TEST_ASSERT_EQUAL(reads, bus.reads);
        TEST_ASSERT_FALSE(sample.valid);
        TEST_ASSERT_TRUE(std::isnan(sample.ax));
    }
    for (int reg : {0xD0, 0xF4, 0xF5}) {
        FakeSensorBus bus;
        SensorValidity sensors;
        SensorSample sample;
        TEST_ASSERT_TRUE(sensors.begin(bus));
        TEST_ASSERT_TRUE(sensors.read(bus, 1, sample));
        bus.registers[0x76][reg] ^= 0x08;
        TEST_ASSERT_FALSE(sensors.read(bus, 2, sample));
        TEST_ASSERT_FALSE(sample.valid);
        TEST_ASSERT_TRUE(std::isnan(sample.altitude_m));
        TEST_ASSERT_FALSE(sensors.controlReady());
    }
}

void test_sensor_fault_command_gate_preserves_emergency_paths() {
    CommandProcessor processor;
    TEST_ASSERT_EQUAL(COMMAND_NACK_SENSOR_INVALID,
                      processor.process("arm", false, true, false).result);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, processor.state());
    TEST_ASSERT_TRUE(processor.process("arm", false, true, true).accepted());
    TEST_ASSERT_EQUAL(COMMAND_NACK_SENSOR_INVALID,
                      processor.process("auto_on", false, true, false).result);
    TEST_ASSERT_EQUAL(COMMAND_NACK_SENSOR_INVALID,
                      processor.process("set_servo:91,91", false, true, false).result);
    TEST_ASSERT_TRUE(processor.process("auto_off", false, true, false).accepted());
    TEST_ASSERT_TRUE(processor.process("deploy_chute", false, true, false).accepted());
    TEST_ASSERT_TRUE(processor.process("estop", false, true, false).accepted());
    TEST_ASSERT_TRUE(processor.process("deploy_chute", false, true, false).accepted());
    TEST_ASSERT_EQUAL(COMMAND_NACK_ESTOP_LATCHED,
                      processor.process("arm", false, true, false).result);
    TEST_ASSERT_TRUE(processor.process("reset", false, true, false).accepted());
    TEST_ASSERT_FALSE(processor.autoEnabled());
    TEST_ASSERT_EQUAL_STRING("sensor_invalid",
                            CommandProcessor::resultText(COMMAND_NACK_SENSOR_INVALID));
}

void test_sensor_fault_reset_never_restores_control() {
    FakeSensorBus bus;
    SensorValidity sensors;
    SensorSample sample;
    CommandProcessor processor;
    TEST_ASSERT_TRUE(sensors.begin(bus));
    TEST_ASSERT_TRUE(sensors.read(bus, 1, sample));
    TEST_ASSERT_TRUE(processor.process("arm", false, true,
                                       sensors.controlReady()).accepted());
    TEST_ASSERT_TRUE(processor.process("auto_on", false, true,
                                       sensors.controlReady()).accepted());
    bus.present[0x68] = false;
    TEST_ASSERT_FALSE(sensors.read(bus, 2, sample));
    processor.disableAutoForSafety();
    TEST_ASSERT_FALSE(processor.autoEnabled());
    TEST_ASSERT_EQUAL(COMMAND_NACK_SENSOR_INVALID,
                      processor.process("auto_on", false, true,
                                        sensors.controlReady()).result);
    TEST_ASSERT_TRUE(processor.process("estop", false, true,
                                       sensors.controlReady()).accepted());
    TEST_ASSERT_TRUE(processor.process("reset", false, true,
                                       sensors.controlReady()).accepted());
    bus.present[0x68] = true;
    TEST_ASSERT_FALSE(sensors.read(bus, 3, sample));
    TEST_ASSERT_EQUAL(COMMAND_NACK_SENSOR_INVALID,
                      processor.process("arm", false, true,
                                        sensors.controlReady()).result);
    TEST_ASSERT_FALSE(processor.autoEnabled());
}

void test_sensor_fault_transport_command_parity() {
    CommandLineBuffer serial, serial2;
    const char* command = "arm\n";
    for (; *command; ++command) { serial.push(*command); serial2.push(*command); }
    CommandProcessor usb_processor, wifi_processor;
    CommandDecision usb = usb_processor.process(serial.line(), false, true, false);
    CommandDecision wifi = wifi_processor.process(serial2.line(), false, true, false);
    TEST_ASSERT_EQUAL(COMMAND_NACK_SENSOR_INVALID, usb.result);
    TEST_ASSERT_EQUAL(usb.result, wifi.result);
    TEST_ASSERT_EQUAL(usb.action, wifi.action);
    TEST_ASSERT_EQUAL(COMMAND_IDLE, usb_processor.state());
    TEST_ASSERT_EQUAL(COMMAND_IDLE, wifi_processor.state());
}

#endif
