#ifndef NATIVE_FAKE_ARDUINO_H
#define NATIVE_FAKE_ARDUINO_H

// Native software boundary only: captures writes; no OS serial port or hardware.
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <sstream>
#include <string>

const int USART2 = 2, PA6 = 6, PA7 = 7, PB0 = 16;
const double PI = 3.14159265358979323846;
static unsigned long fake_millis = 0;
inline unsigned long millis() { return fake_millis; }
inline unsigned long micros() { return fake_millis * 1000; }
inline void delay(unsigned long duration) { fake_millis += duration; }
template <typename T> T constrain(T value, T low, T high) {
    return value < low ? low : (value > high ? high : value);
}

class String {
public:
    std::string value;
    String(const char* text) : value(text) {}
    String(const std::string& text) : value(text) {}
    String(int number) : value(std::to_string(number)) {}
    String(unsigned long number) : value(std::to_string(number)) {}
    String(unsigned int number) : value(std::to_string(number)) {}
    String(float number, int decimals) {
        std::ostringstream out;
        out << std::fixed << std::setprecision(decimals) << number;
        value = out.str();
    }
    friend String operator+(const String& left, const String& right) {
        return String(left.value + right.value);
    }
};

class Print {
public:
    std::string output;
    void print(const char* value) { output += value; }
    void print(const String& value) { output += value.value; }
    void print(int value) { output += std::to_string(value); }
    void print(unsigned int value) { output += std::to_string(value); }
    void print(unsigned long value) { output += std::to_string(value); }
    template <typename T> void println(const T& value) { print(value); output += '\n'; }
};

class Stream : public Print {
public:
    std::string input;
    int available() { return static_cast<int>(input.size()); }
    int read() {
        if (input.empty()) return -1;
        const unsigned char value = static_cast<unsigned char>(input[0]);
        input.erase(0, 1);
        return value;
    }
};

class HardwareSerial : public Stream {
public:
    explicit HardwareSerial(int) {}
    void begin(int) {}
};

static HardwareSerial Serial(1);
#endif
