#ifndef WIRE_SENSOR_BUS_H
#define WIRE_SENSOR_BUS_H

#include <Arduino.h>
#include <Wire.h>
#include "sensor_validity.h"

class WireSensorBus : public SensorBus {
public:
    static const unsigned long SAMPLE_IO_BUDGET_MS = 25;
    void beginSample() { sample_start_ms_ = millis(); sample_budget_active_ = true; }
    bool sampleBudgetExpired() const {
        return sample_budget_active_ && millis() - sample_start_ms_ >= SAMPLE_IO_BUDGET_MS;
    }
    bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) override {
        Wire.beginTransmission(address);
        if (Wire.write(reg) != 1 || Wire.write(value) != 1) {
            Wire.endTransmission();
            return false;
        }
        return Wire.endTransmission() == 0;
    }

    size_t readRegisters(uint8_t address, uint8_t reg, uint8_t* output,
                         size_t length) override {
        if (sampleBudgetExpired()) return 0;
        Wire.beginTransmission(address);
        if (Wire.write(reg) != 1) { Wire.endTransmission(); return 0; }
        if (Wire.endTransmission(false) != 0) return 0;
        if (sampleBudgetExpired()) return 0;
        const size_t received = Wire.requestFrom(address, static_cast<uint8_t>(length));
        if (received != length || Wire.available() != static_cast<int>(length)) {
            while (Wire.available()) Wire.read();
            return received == length ? 0 : received;
        }
        for (size_t i = 0; i < length; ++i) {
            const int value = Wire.read();
            if (value < 0) return i;
            output[i] = static_cast<uint8_t>(value);
        }
        if (sampleBudgetExpired()) return 0;
        return length;
    }

    void waitMilliseconds(uint16_t duration) override { delay(duration); }
private:
    unsigned long sample_start_ms_ = 0;
    bool sample_budget_active_ = false;
};

#endif
