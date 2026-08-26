#include "command_processor.h"

#include <ctype.h>
#include <errno.h>
#include <cmath>
#include <stdlib.h>
#include <string.h>

namespace {
const size_t MAX_COMMAND_BYTES = 128;

bool copyTrimmed(const char* input, char* output, size_t output_size) {
    if (!input || output_size == 0) return false;
    while (*input && isspace(static_cast<unsigned char>(*input))) input++;
    size_t length = strlen(input);
    while (length > 0 && isspace(static_cast<unsigned char>(input[length - 1]))) length--;
    if (length == 0 || length > MAX_COMMAND_BYTES || length >= output_size) return false;
    memcpy(output, input, length);
    output[length] = '\0';
    return true;
}

bool parseInteger(const char*& cursor, long& value) {
    if (!cursor || *cursor == '\0') return false;
    errno = 0;
    char* end = 0;
    value = strtol(cursor, &end, 10);
    if (end == cursor || errno == ERANGE) return false;
    cursor = end;
    return true;
}

bool parseFloat(const char*& cursor, float& value) {
    if (!cursor || *cursor == '\0') return false;
    errno = 0;
    char* end = 0;
    value = strtof(cursor, &end);
    if (end == cursor || errno == ERANGE || !std::isfinite(value)) return false;
    cursor = end;
    return true;
}

bool separator(const char*& cursor) {
    if (!cursor || *cursor != ',') return false;
    cursor++;
    return true;
}

}

CommandProcessor::CommandProcessor() : state_(COMMAND_IDLE) {}

void CommandProcessor::resetForTest() {
    state_ = COMMAND_IDLE;
}

void CommandProcessor::disableAutoForSafety() {
    if (state_ == COMMAND_AUTO_ENABLED) state_ = COMMAND_ARMED;
}

CommandDecision CommandProcessor::decision(CommandResultCode result,
                                           CommandAction action,
                                           const char* command_name,
                                           CommandControlState next_state) const {
    CommandDecision output = {};
    output.result = result;
    output.action = action;
    output.state_before = state_;
    output.state_after = next_state;
    output.command_name = command_name;
    return output;
}

CommandDecision CommandProcessor::process(const char* line, bool recovery_deployed,
                                          bool recovery_idle) {
    char command[MAX_COMMAND_BYTES + 1];
    if (!copyTrimmed(line, command, sizeof(command))) {
        return decision(COMMAND_NACK_MALFORMED, ACTION_NONE, "unknown", state_);
    }

    CommandDecision output;

    if (strcmp(command, "estop") == 0) {
        output = decision(COMMAND_ACK, ACTION_ESTOP, "estop", COMMAND_ESTOP_LATCHED);
        state_ = output.state_after;
        return output;
    }

    if (strcmp(command, "reset") == 0) {
        if (state_ != COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "reset", state_);
        }
        output = decision(COMMAND_ACK, ACTION_RESET, "reset", COMMAND_IDLE);
        state_ = output.state_after;
        return output;
    }

    if (strcmp(command, "deploy_chute") == 0) {
        if (state_ == COMMAND_ESTOP_LATCHED || state_ == COMMAND_ARMED ||
            state_ == COMMAND_AUTO_ENABLED) {
            return decision(COMMAND_ACK, ACTION_DEPLOY_CHUTE, "deploy_chute", state_);
        }
        return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "deploy_chute", state_);
    }

    if (strcmp(command, "arm") == 0) {
        if (state_ == COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_ESTOP_LATCHED, ACTION_NONE, "arm", state_);
        }
        if (state_ != COMMAND_IDLE || recovery_deployed || !recovery_idle) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "arm", state_);
        }
        output = decision(COMMAND_ACK, ACTION_ARM, "arm", COMMAND_ARMED);
        state_ = output.state_after;
        return output;
    }

    if (strcmp(command, "auto_on") == 0) {
        if (state_ == COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_ESTOP_LATCHED, ACTION_NONE, "auto_on", state_);
        }
        if (state_ != COMMAND_ARMED || recovery_deployed) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "auto_on", state_);
        }
        output = decision(COMMAND_ACK, ACTION_AUTO_ON, "auto_on", COMMAND_AUTO_ENABLED);
        state_ = output.state_after;
        return output;
    }

    if (strcmp(command, "auto_off") == 0) {
        if (state_ == COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_ESTOP_LATCHED, ACTION_NONE, "auto_off", state_);
        }
        if (state_ != COMMAND_ARMED && state_ != COMMAND_AUTO_ENABLED) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "auto_off", state_);
        }
        output = decision(COMMAND_ACK, ACTION_AUTO_OFF, "auto_off", COMMAND_ARMED);
        state_ = output.state_after;
        return output;
    }

    if (strncmp(command, "set_servo:", 10) == 0) {
        const char* cursor = command + 10;
        long pitch = 0;
        long roll = 0;
        if (!parseInteger(cursor, pitch) || !separator(cursor) ||
            !parseInteger(cursor, roll) || *cursor != '\0') {
            return decision(COMMAND_NACK_MALFORMED, ACTION_NONE, "set_servo", state_);
        }
        if (pitch < 0 || pitch > 180 || roll < 0 || roll > 180) {
            return decision(COMMAND_NACK_OUT_OF_RANGE, ACTION_NONE, "set_servo", state_);
        }
        if (state_ == COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_ESTOP_LATCHED, ACTION_NONE, "set_servo", state_);
        }
        if (state_ != COMMAND_ARMED) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "set_servo", state_);
        }
        output = decision(COMMAND_ACK, ACTION_SET_SERVO, "set_servo", state_);
        output.servo_pitch = static_cast<int>(pitch);
        output.servo_roll = static_cast<int>(roll);
        return output;
    }

    if (strncmp(command, "set_pid:", 8) == 0) {
        const char* cursor = command + 8;
        float kp = 0.0f;
        float ki = 0.0f;
        float kd = 0.0f;
        if (!parseFloat(cursor, kp) || !separator(cursor) ||
            !parseFloat(cursor, ki) || !separator(cursor) ||
            !parseFloat(cursor, kd) || *cursor != '\0') {
            return decision(COMMAND_NACK_MALFORMED, ACTION_NONE, "set_pid", state_);
        }
        if (kp < 0.0f || kp > 10.0f || ki < 0.0f || ki > 5.0f ||
            kd < 0.0f || kd > 10.0f) {
            return decision(COMMAND_NACK_OUT_OF_RANGE, ACTION_NONE, "set_pid", state_);
        }
        if (state_ == COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_ESTOP_LATCHED, ACTION_NONE, "set_pid", state_);
        }
        if (state_ == COMMAND_AUTO_ENABLED) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, "set_pid", state_);
        }
        output = decision(COMMAND_ACK, ACTION_SET_PID, "set_pid", state_);
        output.kp = kp;
        output.ki = ki;
        output.kd = kd;
        return output;
    }

    if (strcmp(command, "set_profile_flight") == 0 ||
        strcmp(command, "set_profile_testbench") == 0) {
        const bool flight = strcmp(command, "set_profile_flight") == 0;
        const char* name = flight ? "set_profile_flight" : "set_profile_testbench";
        if (state_ == COMMAND_ESTOP_LATCHED) {
            return decision(COMMAND_NACK_ESTOP_LATCHED, ACTION_NONE, name, state_);
        }
        if (state_ == COMMAND_AUTO_ENABLED) {
            return decision(COMMAND_NACK_INVALID_STATE, ACTION_NONE, name, state_);
        }
        return decision(COMMAND_ACK,
                        flight ? ACTION_PROFILE_FLIGHT : ACTION_PROFILE_TESTBENCH,
                        name, state_);
    }

    return decision(COMMAND_NACK_UNKNOWN, ACTION_NONE, "unknown", state_);
}

const char* CommandProcessor::resultText(CommandResultCode result) {
    switch (result) {
        case COMMAND_ACK: return "accepted";
        case COMMAND_NACK_MALFORMED: return "malformed";
        case COMMAND_NACK_INVALID_STATE: return "invalid_state";
        case COMMAND_NACK_OUT_OF_RANGE: return "out_of_range";
        case COMMAND_NACK_ESTOP_LATCHED: return "estop_latched";
        case COMMAND_NACK_UNKNOWN: return "unknown_command";
    }
    return "unknown_command";
}

const char* CommandProcessor::stateText(CommandControlState state) {
    switch (state) {
        case COMMAND_IDLE: return "idle";
        case COMMAND_ARMED: return "armed";
        case COMMAND_AUTO_ENABLED: return "auto_control_enabled";
        case COMMAND_ESTOP_LATCHED: return "estop_latched";
    }
    return "unknown";
}
