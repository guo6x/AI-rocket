#include "pid.h"
#include <Arduino.h>

const float PIDController::INTEGRAL_MAX = 5.0f;  // 同步仿真 integral_limit=3.0, 留余量

// ============ 预设参数 (同步自仿真) ============
// FLIGHT: aero_sim/control_simulation.py
//   Kp=1.0, Ki=0.1, Kd=0.3, max_deflection=4.0°, rate_limit=0.3°/step
//   增益调度: alpha>10° 时 Kp×0.3
// TESTBENCH: dynamics_sim 推荐 (0.5m 高重心 + 50ms 延迟)
//   Kp=1.65, Ki=0.0, Kd=0.45, 无增益调度
PIDController::PIDController(Profile profile)
    : target(0.0f), integral(0.0f), last_error(0.0f), last_output(0.0f) {
    applyProfile(profile);
}

PIDController::PIDController(float kp, float ki, float kd)
    : kp(kp), ki(ki), kd(kd), target(0.0f),
      integral(0.0f), last_error(0.0f), last_output(0.0f),
      output_limit(15.0f), rate_limit(1.0f),
      gs_threshold(1e6f), gs_scale(1.0f) {}

void PIDController::applyProfile(Profile profile) {
    if (profile == FLIGHT) {
        // 飞行用: 同步自 6DOF 仿真验证 (重扰动下落点漂移 105m→22m)
        kp = 1.0f;
        ki = 0.1f;
        kd = 0.3f;
        output_limit = 4.0f;       // max_deflection
        rate_limit = 0.3f;         // deg/step (50ms 步长)
        gs_threshold = 10.0f;      // 攻角 > 10° 触发增益调度
        gs_scale = 0.3f;           // 大攻角 Kp×0.3
    } else {
        // 倒立摆测试台: dynamics_sim 推荐
        kp = 1.65f;
        ki = 0.0f;
        kd = 0.45f;
        output_limit = 15.0f;      // 测试台舵机行程大
        rate_limit = 1.0f;
        gs_threshold = 1e6f;       // 不启用增益调度
        gs_scale = 1.0f;
    }
}

void PIDController::setProfile(Profile profile) {
    applyProfile(profile);
    reset();
}

void PIDController::setGains(float kp, float ki, float kd) {
    this->kp = kp;
    this->ki = ki;
    this->kd = kd;
}

void PIDController::setTarget(float target) {
    this->target = target;
}

void PIDController::reset() {
    integral = 0.0f;
    last_error = 0.0f;
    last_output = 0.0f;
}

void PIDController::setOutputLimit(float max_output_deg) {
    output_limit = max_output_deg;
}

void PIDController::setRateLimit(float max_rate_per_step) {
    rate_limit = max_rate_per_step;
}

void PIDController::setGainScheduling(float threshold_deg, float scale) {
    gs_threshold = threshold_deg;
    gs_scale = scale;
}

float PIDController::compute(float current, float dt) {
    float error = target - current;

    // 积分项 (带限幅)
    integral += error * dt;
    integral = constrain(integral, -INTEGRAL_MAX, INTEGRAL_MAX);

    // 微分项
    float derivative = (error - last_error) / dt;
    last_error = error;

    // 增益调度: 大误差时降低 Kp (避免过激反应导致发散)
    float kp_eff = kp;
    if (fabsf(error) > gs_threshold) {
        kp_eff = kp * gs_scale;
    }

    // PID 输出
    float output = kp_eff * error + ki * integral + kd * derivative;

    // 输出限幅
    output = constrain(output, -output_limit, output_limit);

    // 速率限制 (防舵机过激, 同步仿真 rate_limit=0.3°/step)
    if (output > last_output + rate_limit) output = last_output + rate_limit;
    if (output < last_output - rate_limit) output = last_output - rate_limit;
    last_output = output;

    return output;
}
