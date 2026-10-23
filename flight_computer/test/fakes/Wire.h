#ifndef NATIVE_FAKE_WIRE_H
#define NATIVE_FAKE_WIRE_H

#include "../../src/sensor_validity.h"

class FakeWire {
public:
    SensorBus* bus = nullptr;
    int pointer_nack = 0, write_failure = 0, negative_read_index = -1;
    unsigned long read_advance_ms = 0;
    bool short_buffer = false;
    void begin() {}
    void setClock(unsigned long) {}
    void beginTransmission(uint8_t address) { address_ = address; tx_length_ = 0; }
    size_t write(uint8_t value) {
        if (write_failure) return 0;
        if (tx_length_ < 2) tx_[tx_length_++] = value;
        return 1;
    }
    int endTransmission(bool = true) {
        if (tx_length_ == 1) { register_ = tx_[0]; return pointer_nack; }
        return bus && tx_length_ == 2 && bus->writeRegister(address_, tx_[0], tx_[1]) ? 0 : 2;
    }
    size_t requestFrom(uint8_t address, uint8_t length) {
        fake_millis += read_advance_ms; // deterministic time, never sleep
        rx_index_ = 0;
        rx_length_ = bus ? bus->readRegisters(address, register_, rx_, length) : 0;
        const size_t reported = rx_length_;
        if (short_buffer && rx_length_) --rx_length_;
        return reported;
    }
    int available() { return static_cast<int>(rx_length_ - rx_index_); }
    int read() {
        if (rx_index_ >= rx_length_) return -1;
        const size_t index = rx_index_++;
        return static_cast<int>(index) == negative_read_index ? -1 : rx_[index];
    }
private:
    uint8_t address_ = 0, register_ = 0, tx_[2] = {}, rx_[32] = {};
    size_t tx_length_ = 0, rx_length_ = 0, rx_index_ = 0;
};

static FakeWire Wire;
#endif
