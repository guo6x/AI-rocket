"""
Ad Astra — 2D TVC 倒立摆仿真 (扩展自 1D physics_engine.py)
============================================================
状态向量: [theta_x, theta_y, omega_x, omega_y]
- theta_x: 绕 x 轴俯仰角 (rad), 竖直向上为 0
- theta_y: 绕 y 轴偏航角 (rad), 竖直向上为 0
- omega_x/y: 对应角速度

复用 components.py 的 SensorModel + ServoModel (含 50ms 延迟/0.5° 死区/600°/s 速率限制)
复用固件 pid.cpp 的 PID 算法 (含增益调度+速率限制)

用途: 地面 TVC 测试台 2D 验证 + 跟 aero_sim/sixdof_simulation.py 6DOF 交叉验证

修复记录:
- 单位 bug: math.degrees(error/output) 误用 (输入已是度) → 移除
- 速率限制: PID 改为 1000Hz 运行 (每 dt 步调用), rate_limit 单位 deg/step
- 参考 test_polarity.py 验证极性: theta>0 → servo>0 → tau_thrust<0 → 恢复
- 加 TUNED profile (匹配 test_polarity.py 工作参数 kp=2.0/kd=0.5, 无速率限制)
"""
import os
import sys
import math
import json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from components import SensorModel, ServoModel
from physics_engine import InvertedPendulum1D

OUTPUT_DIR = os.path.dirname(__file__)


class PIDController2D:
    """2D PID 控制器 (同步固件 pid.cpp 算法)
    - 增益调度: 误差>10° 时 Kp×0.3 (仅 FLIGHT)
    - 速率限制: deg/step (每次 compute 调用算一步)
    - 输出限幅: 4° (飞行) / 15° (测试台/TUNED)
    - 输入输出单位: 度
    - profile:
        FLIGHT    — Kp=1.0/Ki=0.1/Kd=0.3 + 增益调度 + 0.3°/step 速率限制 (同步固件)
        TESTBENCH — Kp=1.65/Kd=0.45 + 1.0°/step 速率限制 (同步固件)
        TUNED     — Kp=2.0/Kd=0.5, 无速率限制 (匹配 test_polarity.py 1D 工作参数)
    """
    def __init__(self, profile="FLIGHT"):
        if profile == "FLIGHT":
            self.kp, self.ki, self.kd = 1.0, 0.1, 0.3
            self.output_limit = 4.0
            self.rate_limit = 0.3
            self.gs_threshold = 10.0
            self.gs_scale = 0.3
        elif profile == "TESTBENCH":
            self.kp, self.ki, self.kd = 1.65, 0.0, 0.45
            self.output_limit = 15.0
            self.rate_limit = 1.0
            self.gs_threshold = 1e6
            self.gs_scale = 1.0
        else:  # TUNED
            self.kp, self.ki, self.kd = 2.0, 0.0, 0.5
            self.output_limit = 15.0
            self.rate_limit = 15.0  # 等效无速率限制
            self.gs_threshold = 1e6
            self.gs_scale = 1.0
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.last_error_x = 0.0
        self.last_error_y = 0.0
        self.last_output_x = 0.0
        self.last_output_y = 0.0
        self.integral_max = 5.0

    def reset(self):
        self.integral_x = self.integral_y = 0.0
        self.last_error_x = self.last_error_y = 0.0
        self.last_output_x = self.last_output_y = 0.0

    def compute(self, current_x, current_y, dt):
        """返回 (tvc_pitch_deg, tvc_yaw_deg)
        输入 current_* 单位: 度
        控制极性: theta > 0 → servo > 0 → tau_thrust < 0 → 推回 0
        (跟 test_polarity.py 的 cmd = -pid.compute(0, theta) 等价: error=+theta)
        """
        outputs = []
        for axis, current in enumerate([current_x, current_y]):
            error = current  # target=0, error = current (单位:度)
            integral = self.integral_x if axis == 0 else self.integral_y
            last_error = self.last_error_x if axis == 0 else self.last_error_y
            last_output = self.last_output_x if axis == 0 else self.last_output_y

            integral += error * dt
            integral = max(-self.integral_max, min(self.integral_max, integral))
            derivative = (error - last_error) / dt if dt > 0 else 0.0

            kp_eff = self.kp
            if abs(error) > self.gs_threshold:
                kp_eff = self.kp * self.gs_scale

            output = kp_eff * error + self.ki * integral + self.kd * derivative
            output = max(-self.output_limit, min(self.output_limit, output))

            if output > last_output + self.rate_limit:
                output = last_output + self.rate_limit
            if output < last_output - self.rate_limit:
                output = last_output - self.rate_limit

            if axis == 0:
                self.integral_x = integral
                self.last_error_x = error
                self.last_output_x = output
            else:
                self.integral_y = integral
                self.last_error_y = error
                self.last_output_y = output

            outputs.append(output)

        return outputs[0], outputs[1]


class InvertedPendulum2D:
    """2D TVC 倒立摆物理模型 (双轴解耦)"""
    def __init__(self, mass=1.0, length_cg=0.5, length_thrust=0.5, max_thrust=15.0):
        self.m = mass
        self.L_cg = length_cg
        self.L_t = length_thrust
        self.F_max = max_thrust
        self.g = 9.81
        self.I = (1.0 / 3.0) * self.m * (self.L_cg * 2.0) ** 2
        self.state = [0.0, 0.0, 0.0, 0.0]
        self.time = 0.0

    def reset(self, initial_pitch_deg=0.0, initial_yaw_deg=0.0):
        self.state = [
            math.radians(initial_pitch_deg),
            math.radians(initial_yaw_deg),
            0.0, 0.0
        ]
        self.time = 0.0
        return self.state

    def _derivatives_axis(self, theta, omega, servo_angle_rad, thrust):
        tau_gravity = self.m * self.g * self.L_cg * math.sin(theta)
        tau_thrust = -thrust * self.L_t * math.sin(servo_angle_rad)
        tau_damping = -0.5 * omega
        tau_total = tau_gravity + tau_thrust + tau_damping
        theta_ddot = tau_total / self.I
        return [omega, theta_ddot]

    def _rk4_axis(self, theta, omega, servo_angle_rad, thrust, dt):
        s = [theta, omega]
        k1 = self._derivatives_axis(s[0], s[1], servo_angle_rad, thrust)
        s2 = [s[0] + 0.5 * dt * k1[0], s[1] + 0.5 * dt * k1[1]]
        k2 = self._derivatives_axis(s2[0], s2[1], servo_angle_rad, thrust)
        s3 = [s[0] + 0.5 * dt * k2[0], s[1] + 0.5 * dt * k2[1]]
        k3 = self._derivatives_axis(s3[0], s3[1], servo_angle_rad, thrust)
        s4 = [s[0] + dt * k3[0], s[1] + dt * k3[1]]
        k4 = self._derivatives_axis(s4[0], s4[1], servo_angle_rad, thrust)
        new_theta = s[0] + (dt / 6.0) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        new_omega = s[1] + (dt / 6.0) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        return new_theta, new_omega

    def step(self, dt, servo_pitch_deg, servo_yaw_deg, thrust=None):
        if thrust is None:
            thrust = self.F_max
        theta_x, theta_y, omega_x, omega_y = self.state
        servo_pitch_rad = math.radians(servo_pitch_deg)
        servo_yaw_rad = math.radians(servo_yaw_deg)
        new_theta_x, new_omega_x = self._rk4_axis(
            theta_x, omega_x, servo_pitch_rad, thrust, dt)
        new_theta_y, new_omega_y = self._rk4_axis(
            theta_y, omega_y, servo_yaw_rad, thrust, dt)
        self.state = [new_theta_x, new_theta_y, new_omega_x, new_omega_y]
        self.time += dt
        return (math.degrees(new_theta_x), math.degrees(new_theta_y),
                math.degrees(new_omega_x), math.degrees(new_omega_y))


def run_2d_test(profile="TESTBENCH", initial_perturbation=5.0, duration=10.0,
                cg_height=0.5, with_sensors=True, with_disturbance=True,
                thrust=15.0, mass=1.0):
    """运行 2D 测试"""
    pendulum = InvertedPendulum2D(mass=mass, length_cg=cg_height,
                                  length_thrust=0.5, max_thrust=thrust)
    pendulum.reset(initial_pitch_deg=initial_perturbation,
                   initial_yaw_deg=initial_perturbation * 0.5)

    if with_sensors:
        sensor_x = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
        sensor_y = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
    servo_x = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0,
                         deadband_deg=0.5, speed_deg_per_s=600.0)
    servo_y = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0,
                         deadband_deg=0.5, speed_deg_per_s=600.0)
    pid = PIDController2D(profile=profile)

    dt = 0.001  # 1kHz
    trajectory = []
    max_angle = 0.0

    np.random.seed(42)
    for step_i in range(int(duration / dt)):
        t = step_i * dt
        theta_x = math.degrees(pendulum.state[0])
        theta_y = math.degrees(pendulum.state[1])

        if with_sensors:
            read_x = sensor_x.update(dt, t, theta_x)
            read_y = sensor_y.update(dt, t, theta_y)
        else:
            read_x, read_y = theta_x, theta_y

        # PID 计算 (100Hz, 跟 test_polarity.py 一致; 避免 1kHz 下传感器跳变导致 D 项尖峰)
        if step_i % 10 == 0:
            pid_pitch, pid_yaw = pid.compute(read_x, read_y, dt * 10)
            servo_x.command(pid_pitch)
            servo_y.command(pid_yaw)

        actual_pitch = servo_x.step(dt)
        actual_yaw = servo_y.step(dt)

        disturbance_pitch = 0.0
        disturbance_yaw = 0.0
        if with_disturbance and step_i > 1000 and step_i % 1000 == 0:
            disturbance_pitch = np.random.uniform(-2, 2)
            disturbance_yaw = np.random.uniform(-2, 2)

        pendulum.step(dt, actual_pitch + disturbance_pitch,
                      actual_yaw + disturbance_yaw)

        if step_i % 50 == 0:
            trajectory.append({
                "t": round(t, 3),
                "theta_x": round(theta_x, 3),
                "theta_y": round(theta_y, 3),
                "omega_x": round(math.degrees(pendulum.state[2]), 3),
                "omega_y": round(math.degrees(pendulum.state[3]), 3),
                "servo_pitch": round(actual_pitch, 3),
                "servo_yaw": round(actual_yaw, 3),
                "sensor_x": round(read_x, 3),
                "sensor_y": round(read_y, 3),
            })
            max_angle = max(max_angle, abs(theta_x), abs(theta_y))

        if abs(theta_x) > 60 or abs(theta_y) > 60:
            return {
                "profile": profile,
                "stable": False,
                "max_angle_deg": round(max_angle, 2),
                "rms_final_x": 999.0,
                "rms_final_y": 999.0,
                "duration_s": round(t, 2),
                "verdict": f"发散 @ t={t:.2f}s (角度超 60°)",
                "trajectory": trajectory,
            }

    final_traj = trajectory[-20:]
    rms_x = math.sqrt(sum(p["theta_x"]**2 for p in final_traj) / len(final_traj))
    rms_y = math.sqrt(sum(p["theta_y"]**2 for p in final_traj) / len(final_traj))
    stable = rms_x < 2.0 and rms_y < 2.0

    return {
        "profile": profile,
        "stable": stable,
        "max_angle_deg": round(max_angle, 2),
        "rms_final_x": round(rms_x, 2),
        "rms_final_y": round(rms_y, 2),
        "duration_s": round(pendulum.time, 2),
        "verdict": "稳定收敛" if stable else f"未收敛 (RMS_x={rms_x:.2f}°, RMS_y={rms_y:.2f}°)",
        "trajectory": trajectory,
    }


def main():
    print("=" * 70)
    print("  Ad Astra 2D TVC 倒立摆仿真 (扩展自 1D, 同步固件 PID 算法)")
    print("=" * 70)
    print(f"  物理模型: 1kg, CG=0.5m, L_t=0.5m")
    print(f"  传感器: 20Hz + 50ms 延迟 (可选)")
    print(f"  舵机: 50Hz + 0.5° 死区 + 600°/s")
    print(f"  PID: 1kHz, rate_limit deg/step")
    print()

    test_cases = [
        {"name": "理想 TESTBENCH PID (15N, 5°)",
         "profile": "TESTBENCH", "initial": 5.0, "sensors": False, "thrust": 15.0},
        {"name": "理想 FLIGHT PID (15N, 5°)",
         "profile": "FLIGHT", "initial": 5.0, "sensors": False, "thrust": 15.0},
        {"name": "TESTBENCH PID + 非理想 (15N, 5°)",
         "profile": "TESTBENCH", "initial": 5.0, "sensors": True, "thrust": 15.0},
        {"name": "FLIGHT PID + 非理想 (15N, 5°)",
         "profile": "FLIGHT", "initial": 5.0, "sensors": True, "thrust": 15.0},
        # 完全匹配 test_polarity.py: 1° 初始 + 25N + TUNED 参数
        {"name": "TUNED + 非理想 (25N, 1°, 跟1D完全一致)",
         "profile": "TUNED", "initial": 1.0, "sensors": True, "thrust": 25.0},
        {"name": "TUNED + 非理想 (15N, 1°)",
         "profile": "TUNED", "initial": 1.0, "sensors": True, "thrust": 15.0},
    ]

    results = []
    for tc in test_cases:
        print(f"\n[测试] {tc['name']}")
        out = run_2d_test(
            profile=tc["profile"],
            initial_perturbation=tc["initial"],
            duration=10.0,
            with_sensors=tc.get("sensors", True),
            thrust=tc.get("thrust", 15.0),
        )
        results.append({"name": tc["name"], **{k: v for k, v in out.items() if k != "trajectory"}})
        print(f"  稳定: {out['stable']}")
        print(f"  最大角度: {out['max_angle_deg']}°")
        print(f"  末段 RMS: x={out['rms_final_x']}°, y={out['rms_final_y']}°")
        print(f"  结论: {out['verdict']}")

    print("\n" + "=" * 70)
    print("  对比表")
    print("=" * 70)
    print(f"{'测试':<48s} {'稳定':>6s} {'最大°':>8s} {'RMS_x':>8s} {'RMS_y':>8s}")
    print("-" * 83)
    for r in results:
        stable_str = "OK" if r["stable"] else "X"
        print(f"{r['name']:<48s} {stable_str:>6s} {r['max_angle_deg']:>8.2f} "
              f"{r['rms_final_x']:>8.2f} {r['rms_final_y']:>8.2f}")

    out_file = os.path.join(OUTPUT_DIR, "results_2d.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, ensure_ascii=False, indent=2)
    print(f"\n[输出] {out_file}")


if __name__ == "__main__":
    main()
