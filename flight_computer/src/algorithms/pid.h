#ifndef PID_H
#define PID_H

/**
 * @class PIDController
 * @brief PID 控制器类 (含增益调度+速率限制, 同步自 6DOF 飞行仿真)
 *
 * 参数来源:
 * - 飞行用 (FLIGHT): aero_sim/control_simulation.py Kp=1.0/Ki=0.1/Kd=0.3
 *   仿真验证: 重扰动(5m/s风+0.5°偏斜+5mm偏心)下落点漂移 105m→22m
 * - 测试台 (TESTBENCH): dynamics_sim 推荐 Kp=1.65/Ki=0.0/Kd=0.45
 *   适用于 0.5m 高重心倒立摆 + 50ms 延迟 + 50Hz 舵机
 */
class PIDController {
public:
    /**
     * @brief 预设参数组
     */
    enum Profile {
        FLIGHT = 0,      // 飞行用 (同步自 6DOF 仿真)
        TESTBENCH = 1    // 倒立摆测试台用 (dynamics_sim 推荐)
    };

    /**
     * @brief 构造函数
     * @param profile 参数预设 (默认 FLIGHT)
     */
    PIDController(Profile profile = FLIGHT);

    /** 兼容旧接口: 任意指定增益 */
    PIDController(float kp, float ki, float kd);

    void setGains(float kp, float ki, float kd);
    void setTarget(float target);
    void reset();

    /** 切换参数预设 */
    void setProfile(Profile profile);

    /**
     * @brief 设置输出限幅 (deg)
     */
    void setOutputLimit(float max_output_deg);

    /**
     * @brief 设置输出速率限制 (deg/step)
     * 防止舵机过激反应导致发散
     */
    void setRateLimit(float max_rate_per_step);

    /**
     * @brief 设置增益调度阈值
     * @param threshold_deg 误差超过此值时降低 Kp (避免大攻角下过激)
     * @param scale 大误差时的增益系数 (0~1)
     */
    void setGainScheduling(float threshold_deg, float scale);

    /**
     * @brief 计算 PID 输出
     * @param current 当前值
     * @param dt 时间间隔（秒）
     * @return 控制输出 (已限幅+速率限制)
     */
    float compute(float current, float dt);

    /** 获取上次输出 (调试用) */
    float getLastOutput() const { return last_output; }

private:
    float kp, ki, kd;
    float target;
    float integral;
    float last_error;
    float last_output;

    float output_limit;       // 输出限幅 (deg)
    float rate_limit;         // 速率限制 (deg/step)
    float gs_threshold;       // 增益调度阈值 (deg)
    float gs_scale;           // 大误差增益系数

    static const float INTEGRAL_MAX;

    /** 应用预设参数 */
    void applyProfile(Profile profile);
};

#endif // PID_H
