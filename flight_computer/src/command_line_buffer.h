#ifndef COMMAND_LINE_BUFFER_H
#define COMMAND_LINE_BUFFER_H

#include <stddef.h>

enum CommandLineEvent {
    COMMAND_LINE_NONE,
    COMMAND_LINE_READY,
    COMMAND_LINE_OVERLONG,
    COMMAND_LINE_MALFORMED
};

class CommandLineBuffer {
public:
    static const size_t MAX_BYTES = 128;

    CommandLineBuffer() : length_(0), discarding_(false), overlong_(false) {
        line_[0] = '\0';
    }

    CommandLineEvent push(char value) {
        if (value == '\r') return COMMAND_LINE_NONE;
        if (value == '\n') {
            if (discarding_) {
                const CommandLineEvent event =
                    overlong_ ? COMMAND_LINE_OVERLONG : COMMAND_LINE_MALFORMED;
                reset();
                return event;
            }
            line_[length_] = '\0';
            length_ = 0;
            return COMMAND_LINE_READY;
        }
        if (discarding_) return COMMAND_LINE_NONE;
        if (value == '\0') {
            discarding_ = true;
            overlong_ = false;
            length_ = 0;
            line_[0] = '\0';
            return COMMAND_LINE_NONE;
        }
        if (length_ >= MAX_BYTES) {
            discarding_ = true;
            overlong_ = true;
            length_ = 0;
            line_[0] = '\0';
            return COMMAND_LINE_NONE;
        }
        line_[length_++] = value;
        line_[length_] = '\0';
        return COMMAND_LINE_NONE;
    }

    const char* line() const { return line_; }
    bool discarding() const { return discarding_; }

    void reset() {
        length_ = 0;
        discarding_ = false;
        overlong_ = false;
        line_[0] = '\0';
    }

private:
    char line_[MAX_BYTES + 1];
    size_t length_;
    bool discarding_;
    bool overlong_;
};

#endif
