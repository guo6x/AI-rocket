#ifndef FLIGHT_FSM_H
#define FLIGHT_FSM_H

#include <Arduino.h>

/**
 * @enum FlightState
 * @brief 飞行阶段枚举
 */
enum FlightState { FS_IDLE, FS_ARMED, FS_POWERED, FS_COAST, FS_DESCENT, FS_LANDED };

/**
 * @class FlightStateMachine
 * @brief 飞行状态机类，管理飞行阶段转换和回收逻辑
 */
class FlightStateMachine {
public:
    FlightStateMachine();

    void update(float az, float current_alt, unsigned long now);
    
    // 指令接口
    void arm(float ground_alt);
    void deployChute(const char* source);
    void reset();

    // 状态获取
    FlightState getState() const { return state; }
    const char* getStateStr() const { return state_strings[state]; }
    bool isChuteDeployed() const { return chute_deployed; }
    unsigned long getLaunchTime() const { return launch_time; }

private:
    FlightState state;
    bool chute_deployed;
    
    // 高度历史，用于顶点检测
    float alt_history[5];
    int alt_idx;
    float launch_alt;
    unsigned long launch_time;
    unsigned long arm_start_time;

    // 发射检测
    int launch_counter;

    static const char* state_strings[];
    static const float LAUNCH_ACCEL_THRESHOLD;
    static const int LAUNCH_SAMPLES_REQ;
    static const unsigned long TIMER_DEPLOY_MS;

    void checkLaunchDetection(float az);
    void checkBurnoutDetection(float az);
    void checkApogeeDetection(float current_alt);
    void checkTimerDeploy(unsigned long now);
};

#endif // FLIGHT_FSM_H
