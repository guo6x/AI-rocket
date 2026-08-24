#include "flight_fsm.h"

const char* FlightStateMachine::state_strings[] = {"IDLE", "ARMED", "POWERED", "COAST", "DESCENT", "LANDED"};
const float FlightStateMachine::LAUNCH_ACCEL_THRESHOLD = 2.5f;
const int FlightStateMachine::LAUNCH_SAMPLES_REQ = 3;
const unsigned long FlightStateMachine::TIMER_DEPLOY_MS = 15000;

FlightStateMachine::FlightStateMachine() {
    reset();
}

void FlightStateMachine::reset() {
    state = FS_IDLE;
    chute_deployed = false;
    alt_idx = 0;
    launch_alt = 0;
    launch_time = 0;
    arm_start_time = 0;
    launch_counter = 0;
    for (int i = 0; i < 5; i++) alt_history[i] = 0;
}

void FlightStateMachine::arm(float ground_alt) {
    if (!chute_deployed) {
        state = FS_ARMED;
        launch_alt = ground_alt;
        arm_start_time = millis();
        alt_idx = 0;
        launch_counter = 0;
    }
}

void FlightStateMachine::deployChute(const char* source) {
    if (chute_deployed) return;
    chute_deployed = true;
    state = FS_DESCENT;
    // 注意：舵机操作将由 main.cpp 根据 isChuteDeployed() 状态执行
}

void FlightStateMachine::update(float az, float current_alt, unsigned long now) {
    checkLaunchDetection(az);
    checkBurnoutDetection(az);
    checkApogeeDetection(current_alt);
    checkTimerDeploy(now);
}

void FlightStateMachine::checkLaunchDetection(float az) {
    if (state != FS_ARMED) return;
    
    if (abs(az) > LAUNCH_ACCEL_THRESHOLD) {
        launch_counter++;
        if (launch_counter >= LAUNCH_SAMPLES_REQ) {
            state = FS_POWERED;
            launch_time = millis();
        }
    } else {
        launch_counter = 0;
    }
}

void FlightStateMachine::checkBurnoutDetection(float az) {
    if (state != FS_POWERED) return;
    if (abs(az) < 1.2f) {
        state = FS_COAST;
    }
}

void FlightStateMachine::checkApogeeDetection(float current_alt) {
    if (chute_deployed || state != FS_COAST) return;

    alt_history[alt_idx % 5] = current_alt;
    alt_idx++;
    if (alt_idx >= 5) {
        bool all_desc = true;
        for (int i = 1; i < 5; i++) {
            if (alt_history[i % 5] >= alt_history[(i - 1) % 5]) {
                all_desc = false;
                break;
            }
        }
        if (all_desc) deployChute("APOGEE_DETECT");
    }
}

void FlightStateMachine::checkTimerDeploy(unsigned long now) {
    if (chute_deployed || state == FS_IDLE || state == FS_ARMED) return;
    if (now - launch_time > TIMER_DEPLOY_MS) {
        deployChute("TIMER_BACKUP");
    }
}
