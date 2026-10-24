#ifndef SENSOR_VALIDITY_H
#define SENSOR_VALIDITY_H

#include <stddef.h>
#include <stdint.h>

// Exact-length register IO, shared by the physical Wire adapter and native fake.
class SensorBus {
public:
    virtual bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) = 0;
    virtual size_t readRegisters(uint8_t address, uint8_t reg, uint8_t* output,
                                 size_t length) = 0;
    virtual void waitMilliseconds(uint16_t duration) = 0;
};

enum SensorFault {
    SENSOR_OK,
    SENSOR_NOT_INITIALIZED,
    SENSOR_IMU_MISSING,
    SENSOR_IMU_IDENTITY,
    SENSOR_CONFIG_WRITE,
    SENSOR_CONFIG_READBACK,
    SENSOR_IMU_READ,
    SENSOR_IMU_SAMPLE,
    SENSOR_BMP_MISSING,
    SENSOR_BMP_IDENTITY,
    SENSOR_BMP_STATUS,
    SENSOR_BMP_CALIBRATION,
    SENSOR_BMP_READ,
    SENSOR_BMP_SAMPLE
};

struct SensorSample {
    bool valid;
    uint32_t time_ms;
    float ax, ay, az;        // g, configured +/-2 g
    float gx, gy, gz;        // degrees/s, configured +/-250 degrees/s
    float temperature_c, pressure_pa, altitude_m;
    SensorSample();         // invalid values are NaN, never fabricated zero data
};

// GY-91 is a module/order name, not an identity. Only explicit supported silicon
// IDs are accepted. MPU9250's AK8963 magnetometer is NOT used by this 6-axis path.
class SensorValidity {
public:
    SensorValidity();
    bool begin(SensorBus& bus);
    bool read(SensorBus& bus, uint32_t time_ms, SensorSample& sample);
    bool controlReady() const { return initialized_ && sample_valid_ && !latched_; }
    bool faultLatched() const { return latched_; }
    SensorFault fault() const { return fault_; }
    uint8_t imuAddress() const { return imu_address_; }
    uint8_t imuIdentity() const { return imu_id_; }
    uint8_t bmpAddress() const { return bmp_address_; }
    uint8_t bmpIdentity() const { return bmp_id_; }
    static const char* faultText(SensorFault fault);
    static bool barometerValuesValid(float pressure, float temperature, float altitude);

private:
    bool initialized_, sample_valid_, latched_;
    SensorFault fault_;
    uint8_t imu_address_, imu_id_, bmp_address_, bmp_id_;
    uint16_t dig_t1_, dig_p1_;
    int16_t dig_t2_, dig_t3_, dig_p_[8];

    bool fail(SensorFault fault);
    bool configure(SensorBus& bus, uint8_t address, uint8_t reg, uint8_t value);
    bool configurationMatches(SensorBus& bus, uint8_t address, uint8_t reg,
                               uint8_t expected);
    bool waitBarometerIdle(SensorBus& bus);
};

#endif
