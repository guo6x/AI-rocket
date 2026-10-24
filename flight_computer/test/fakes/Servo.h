#ifndef NATIVE_FAKE_SERVO_H
#define NATIVE_FAKE_SERVO_H
class Servo {
public:
    int pin = -1, last_angle = -1;
    unsigned writes = 0;
    void attach(int value) { pin = value; }
    void write(int angle) { last_angle = angle; ++writes; }
};
#endif
