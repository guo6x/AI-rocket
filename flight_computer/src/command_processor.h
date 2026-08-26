#ifndef COMMAND_PROCESSOR_H
#define COMMAND_PROCESSOR_H

#include <stddef.h>

enum CommandControlState {
    COMMAND_IDLE,
    COMMAND_ARMED,
    COMMAND_AUTO_ENABLED,
    COMMAND_ESTOP_LATCHED
};

enum CommandResultCode {
    COMMAND_ACK,
    COMMAND_NACK_MALFORMED,
    COMMAND_NACK_INVALID_STATE,
    COMMAND_NACK_OUT_OF_RANGE,
    COMMAND_NACK_ESTOP_LATCHED,
    COMMAND_NACK_UNKNOWN
};

enum CommandAction {
    ACTION_NONE,
    ACTION_ARM,
    ACTION_AUTO_ON,
    ACTION_AUTO_OFF,
    ACTION_SET_SERVO,
    ACTION_SET_PID,
    ACTION_ESTOP,
    ACTION_RESET,
    ACTION_DEPLOY_CHUTE,
    ACTION_PROFILE_FLIGHT,
    ACTION_PROFILE_TESTBENCH
};

struct CommandDecision {
    CommandResultCode result;
    CommandAction action;
    CommandControlState state_before;
    CommandControlState state_after;
    const char* command_name;
    int servo_pitch;
    int servo_roll;
    float kp;
    float ki;
    float kd;

    bool accepted() const { return result == COMMAND_ACK; }
};

class CommandProcessor {
public:
    CommandProcessor();

    CommandDecision process(const char* line, bool recovery_deployed = false,
                            bool recovery_idle = true);
    CommandControlState state() const { return state_; }
    bool autoEnabled() const { return state_ == COMMAND_AUTO_ENABLED; }
    bool estopLatched() const { return state_ == COMMAND_ESTOP_LATCHED; }
    void disableAutoForSafety();
    void resetForTest();

    static const char* resultText(CommandResultCode result);
    static const char* stateText(CommandControlState state);

private:
    CommandControlState state_;

    CommandDecision decision(CommandResultCode result, CommandAction action,
                             const char* command_name,
                             CommandControlState next_state) const;
};

#endif
