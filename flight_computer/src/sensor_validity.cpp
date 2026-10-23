#include "sensor_validity.h"

#include <cmath>

namespace {
uint16_t littleWord(const uint8_t* data) {
    return static_cast<uint16_t>(data[0]) |
           static_cast<uint16_t>(static_cast<uint16_t>(data[1]) << 8);
}

int16_t signedWord(uint16_t bits) {
    // Avoid sign extension / left-shifting negative Wire.read() return values.
    return static_cast<int16_t>(bits <= 0x7FFF ? static_cast<int32_t>(bits)
                                              : static_cast<int32_t>(bits) - 65536);
}

int16_t bigSignedWord(const uint8_t* data) {
    return signedWord(static_cast<uint16_t>(static_cast<uint16_t>(data[0]) << 8) |
                      static_cast<uint16_t>(data[1]));
}

uint32_t raw20(const uint8_t* data) {
    return (static_cast<uint32_t>(data[0]) << 12) |
           (static_cast<uint32_t>(data[1]) << 4) | (data[2] >> 4);
}

bool uniformBytes(const uint8_t* data, size_t length, uint8_t value) {
    for (size_t i = 0; i < length; ++i) if (data[i] != value) return false;
    return true;
}
}

SensorSample::SensorSample()
    : valid(false), time_ms(0), ax(NAN), ay(NAN), az(NAN),
      gx(NAN), gy(NAN), gz(NAN), temperature_c(NAN), pressure_pa(NAN), altitude_m(NAN) {}

SensorValidity::SensorValidity()
    : initialized_(false), sample_valid_(false), latched_(false),
      fault_(SENSOR_NOT_INITIALIZED), imu_address_(0), imu_id_(0),
      bmp_address_(0), bmp_id_(0), dig_t1_(0), dig_p1_(0),
      dig_t2_(0), dig_t3_(0), dig_p_{} {}

bool SensorValidity::fail(SensorFault fault) {
    if (!latched_) fault_ = fault;
    latched_ = true;
    sample_valid_ = false;
    return false;
}

bool SensorValidity::configurationMatches(SensorBus& bus, uint8_t address,
                                          uint8_t reg, uint8_t expected) {
    uint8_t actual = 0;
    return bus.readRegisters(address, reg, &actual, 1) == 1 && actual == expected;
}

bool SensorValidity::configure(SensorBus& bus, uint8_t address,
                               uint8_t reg, uint8_t value) {
    if (!bus.writeRegister(address, reg, value)) return fail(SENSOR_CONFIG_WRITE);
    if (!configurationMatches(bus, address, reg, value))
        return fail(SENSOR_CONFIG_READBACK);
    return true;
}

bool SensorValidity::waitBarometerIdle(SensorBus& bus) {
    // Normal -> sleep can finish an ongoing conversion first. Wait for both
    // measuring and NVM calibration copying (im_update), at most 100 polls.
    for (unsigned attempt = 0; attempt < 100; ++attempt) {
        uint8_t status = 0;
        if (bus.readRegisters(bmp_address_, 0xF3, &status, 1) != 1)
            return fail(SENSOR_BMP_STATUS);
        if ((status & 0x09) == 0) return true;
        bus.waitMilliseconds(1);
    }
    return fail(SENSOR_BMP_STATUS);
}

bool SensorValidity::begin(SensorBus& bus) {
    // A fault is intentionally reboot-latched. Command RESET and re-calling
    // begin() cannot silently resume automatic output after a sensor failure.
    if (latched_) return false;
    sample_valid_ = false;
    initialized_ = false;
    bool imu_responded = false;
    bool found = false;
    for (uint8_t address = 0x68; address <= 0x69; ++address) {
        uint8_t identity = 0;
        if (bus.readRegisters(address, 0x75, &identity, 1) != 1) continue;
        imu_responded = true;
        imu_address_ = address;
        imu_id_ = identity;
        if (identity == 0x70 || identity == 0x71) { found = true; break; }
    }
    if (!found) return fail(imu_responded ? SENSOR_IMU_IDENTITY : SENSOR_IMU_MISSING);

    // Explicitly configure the full-scale assumptions already used by control.
    if (!configure(bus, imu_address_, 0x6B, 0x00)) return false; // awake/internal clock
    bus.waitMilliseconds(100);
    if (!configure(bus, imu_address_, 0x6C, 0x00) || // all six axes enabled
        !configure(bus, imu_address_, 0x1B, 0x00) || // gyro +/-250 degrees/s
        !configure(bus, imu_address_, 0x1C, 0x00)) return false; // accel +/-2 g

    bool bmp_responded = false;
    found = false;
    for (uint8_t address = 0x76; address <= 0x77; ++address) {
        uint8_t identity = 0;
        if (bus.readRegisters(address, 0xD0, &identity, 1) != 1) continue;
        bmp_responded = true;
        bmp_address_ = address;
        bmp_id_ = identity;
        if (identity == 0x58) { found = true; break; }
    }
    if (!found) return fail(bmp_responded ? SENSOR_BMP_IDENTITY : SENSOR_BMP_MISSING);

    if (!bus.writeRegister(bmp_address_, 0xF4, 0x00)) return fail(SENSOR_CONFIG_WRITE);
    if (!waitBarometerIdle(bus)) return false;
    if (!configurationMatches(bus, bmp_address_, 0xF4, 0x00))
        return fail(SENSOR_CONFIG_READBACK);

    uint8_t calibration[24];
    if (bus.readRegisters(bmp_address_, 0x88, calibration, sizeof(calibration)) !=
            sizeof(calibration) || uniformBytes(calibration, sizeof(calibration), 0) ||
        uniformBytes(calibration, sizeof(calibration), 0xFF))
        return fail(SENSOR_BMP_CALIBRATION);
    dig_t1_ = littleWord(calibration);
    dig_t2_ = signedWord(littleWord(calibration + 2));
    dig_t3_ = signedWord(littleWord(calibration + 4));
    dig_p1_ = littleWord(calibration + 6);
    for (unsigned i = 0; i < 8; ++i)
        dig_p_[i] = signedWord(littleWord(calibration + 8 + 2 * i));
    if (dig_t1_ == 0 || dig_p1_ == 0) return fail(SENSOR_BMP_CALIBRATION);

    // Sleep before changing config; preserve the prior x2/x16/filter16 settings.
    if (!configure(bus, bmp_address_, 0xF5, 0x10) ||
        !configure(bus, bmp_address_, 0xF4, 0x57)) return false;
    bus.waitMilliseconds(100); // first normal-mode conversion must finish
    initialized_ = true;
    fault_ = SENSOR_OK;
    return true;
}

bool SensorValidity::barometerValuesValid(float pressure, float temperature, float altitude) {
    // BMP280 specified operating range, not a calibration/accuracy assertion.
    return std::isfinite(pressure) && pressure >= 30000.0f && pressure <= 110000.0f &&
           std::isfinite(temperature) && temperature >= -40.0f && temperature <= 85.0f &&
           std::isfinite(altitude);
}

bool SensorValidity::read(SensorBus& bus, uint32_t time_ms, SensorSample& sample) {
    sample = SensorSample();
    sample.time_ms = time_ms;
    sample_valid_ = false; // invalidate prior data before any bus transaction
    if (latched_) return false;
    if (!initialized_) return fail(SENSOR_NOT_INITIALIZED);
    if (!configurationMatches(bus, imu_address_, 0x75, imu_id_))
        return fail(SENSOR_IMU_IDENTITY);
    if (!configurationMatches(bus, imu_address_, 0x6B, 0) ||
        !configurationMatches(bus, imu_address_, 0x6C, 0) ||
        !configurationMatches(bus, imu_address_, 0x1B, 0) ||
        !configurationMatches(bus, imu_address_, 0x1C, 0))
        return fail(SENSOR_CONFIG_READBACK);
    if (!configurationMatches(bus, bmp_address_, 0xD0, bmp_id_))
        return fail(SENSOR_BMP_IDENTITY);
    if (!configurationMatches(bus, bmp_address_, 0xF4, 0x57) ||
        !configurationMatches(bus, bmp_address_, 0xF5, 0x10))
        return fail(SENSOR_CONFIG_READBACK);

    uint8_t imu[14];
    if (bus.readRegisters(imu_address_, 0x3B, imu, sizeof(imu)) != sizeof(imu))
        return fail(SENSOR_IMU_READ);
    // All-zero/all-FF bus frames or an exactly zero acceleration vector provide
    // no usable tilt observation. This is not a vibration/stuck-sensor detector.
    const int16_t raw_ax = bigSignedWord(imu), raw_ay = bigSignedWord(imu + 2),
                  raw_az = bigSignedWord(imu + 4);
    if (uniformBytes(imu, sizeof(imu), 0xFF) ||
        (raw_ax == 0 && raw_ay == 0 && raw_az == 0)) return fail(SENSOR_IMU_SAMPLE);

    uint8_t bmp[6];
    if (bus.readRegisters(bmp_address_, 0xF7, bmp, sizeof(bmp)) != sizeof(bmp))
        return fail(SENSOR_BMP_READ);
    const uint32_t adc_p = raw20(bmp), adc_t = raw20(bmp + 3);
    if (uniformBytes(bmp, sizeof(bmp), 0) || uniformBytes(bmp, sizeof(bmp), 0xFF) ||
        adc_p == 0x80000 || adc_t == 0x80000) return fail(SENSOR_BMP_SAMPLE);

    // Bosch BMP280 datasheet section 3.11.3 floating-point compensation.
    // Unlike library getters that discard bus status, both raw values above
    // originate in one checked six-byte transaction; calibration was checked too.
    float t1 = (adc_t / 16384.0f - dig_t1_ / 1024.0f) * dig_t2_;
    float t2 = adc_t / 131072.0f - dig_t1_ / 8192.0f;
    t2 = t2 * t2 * dig_t3_;
    const float fine = t1 + t2;
    const float temperature = fine / 5120.0f;
    float p1 = fine / 2.0f - 64000.0f;
    float p2 = p1 * p1 * dig_p_[4] / 32768.0f;
    p2 += p1 * dig_p_[3] * 2.0f;
    p2 = p2 / 4.0f + dig_p_[2] * 65536.0f;
    p1 = (dig_p_[1] * p1 * p1 / 524288.0f + dig_p_[0] * p1) / 524288.0f;
    p1 = (1.0f + p1 / 32768.0f) * dig_p1_;
    if (!std::isfinite(p1) || p1 <= 0) return fail(SENSOR_BMP_SAMPLE);
    float pressure = (1048576.0f - adc_p - p2 / 4096.0f) * 6250.0f / p1;
    p1 = dig_p_[7] * pressure * pressure / 2147483648.0f;
    p2 = pressure * dig_p_[6] / 32768.0f;
    pressure += (p1 + p2 + dig_p_[5]) / 16.0f;
    const float altitude = 44330.0f * (1.0f - std::pow(pressure / 101325.0f, 0.1903f));
    if (!barometerValuesValid(pressure, temperature, altitude)) return fail(SENSOR_BMP_SAMPLE);

    sample.ax = raw_ax / 16384.0f;
    sample.ay = raw_ay / 16384.0f;
    sample.az = raw_az / 16384.0f;
    sample.gx = bigSignedWord(imu + 8) / 131.0f;
    sample.gy = bigSignedWord(imu + 10) / 131.0f;
    sample.gz = bigSignedWord(imu + 12) / 131.0f;
    sample.temperature_c = temperature;
    sample.pressure_pa = pressure;
    sample.altitude_m = altitude;
    sample.valid = sample_valid_ = true;
    return true;
}

const char* SensorValidity::faultText(SensorFault fault) {
    switch (fault) {
        case SENSOR_OK: return "valid";
        case SENSOR_NOT_INITIALIZED: return "not_initialized";
        case SENSOR_IMU_MISSING: return "imu_missing";
        case SENSOR_IMU_IDENTITY: return "imu_identity";
        case SENSOR_CONFIG_WRITE: return "config_write";
        case SENSOR_CONFIG_READBACK: return "config_readback";
        case SENSOR_IMU_READ: return "imu_read";
        case SENSOR_IMU_SAMPLE: return "imu_sample";
        case SENSOR_BMP_MISSING: return "bmp_missing";
        case SENSOR_BMP_IDENTITY: return "bmp_identity";
        case SENSOR_BMP_STATUS: return "bmp_status";
        case SENSOR_BMP_CALIBRATION: return "bmp_calibration";
        case SENSOR_BMP_READ: return "bmp_read";
        case SENSOR_BMP_SAMPLE: return "bmp_sample";
    }
    return "unknown";
}
