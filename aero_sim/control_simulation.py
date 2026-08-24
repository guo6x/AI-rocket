"""
Ad Astra — 飞控算法仿真 (Phase 3)
==================================
在 6DOF 仿真器中注入 PID 控制律, 验证 TVC 主动控制效果

控制目标: 让箭体轴向对准速度方向 (零攻角飞行)
控制律: α_TVC = -Kp * α_attack - Kd * ω_pitch
- α_attack: 当前攻角 (箭体轴向 vs 速度方向的夹角)
- ω_pitch: body frame 角速度 (俯仰/偏航分量)
- α_TVC: 推力矢量偏转角 (deg)

测试场景:
1. 开环 (无控制) + 5m/s 侧风 + 0.5° 推力偏斜
2. PID 闭环 + 同样扰动
对比: 落点散布 / 最大攻角 / 姿态稳定性

输出: results/control_comparison.json
"""
import os
import sys
import math
import json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sixdof_simulation import Rocket6DOF, run_baseline, quat_to_rotmat, quat_normalize

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")


def pid_controller(Kp=1.0, Kd=0.3, max_deflection=4.0, integral_limit=3.0):
    """生成 PID 控制律回调
    返回: control_fn(t, state) → (tvc_pitch_deg, tvc_yaw_deg)

    力矩分析 (推力作用点 r=[-L,0,0], F=[F*cos*sin, F*sin(pitch), F*sin(yaw)]):
      M = r × F
      M_y = L * F * sin(yaw)   → 由 tvc_yaw 控制 → 影响 omega[1] → 控制 alpha_z
      M_z = -L * F * sin(pitch) → 由 tvc_pitch 控制 → 影响 omega[2] → 控制 alpha_y

    增益调度: 攻角 > 10° 时降低 Kp (避免大攻角下过激反应)
    """
    state_int = {"iy": 0.0, "iz": 0.0, "last_t": 0.0}
    last_output = {"pitch": 0.0, "yaw": 0.0}
    rate_limit = 0.3  # deg/step

    def control_fn(t, state):
        vel = state[3:6]
        q = quat_normalize(state[6:10])
        omega = state[10:13]  # body frame

        speed = np.linalg.norm(vel)
        if speed < 5.0:
            state_int["last_t"] = t
            return (0.0, 0.0)

        R_bw = quat_to_rotmat(q)
        R_wb = R_bw.T
        vel_body = R_wb @ (vel / speed)
        alpha_y = math.atan2(vel_body[1], vel_body[0])
        alpha_z = math.atan2(vel_body[2], vel_body[0])
        alpha_total = math.hypot(alpha_y, alpha_z)

        # 增益调度: 大攻角时降低增益 (避免发散)
        gain_scale = 1.0 if alpha_total < math.radians(10) else 0.3

        dt = max(t - state_int["last_t"], 1e-4)
        state_int["iy"] += alpha_y * dt
        state_int["iz"] += alpha_z * dt
        state_int["iy"] = max(-integral_limit, min(integral_limit, state_int["iy"]))
        state_int["iz"] = max(-integral_limit, min(integral_limit, state_int["iz"]))
        state_int["last_t"] = t

        Ki = 0.1
        Kp_eff = Kp * gain_scale
        tvc_pitch = -Kp_eff * alpha_y - Kd * omega[2] - Ki * state_int["iy"]
        tvc_yaw = Kp_eff * alpha_z - Kd * omega[1] + Ki * state_int["iz"]

        tvc_pitch_deg = max(-max_deflection, min(max_deflection, math.degrees(tvc_pitch)))
        tvc_yaw_deg = max(-max_deflection, min(max_deflection, math.degrees(tvc_yaw)))

        # 速率限制
        tvc_pitch_deg = max(last_output["pitch"] - rate_limit,
                            min(last_output["pitch"] + rate_limit, tvc_pitch_deg))
        tvc_yaw_deg = max(last_output["yaw"] - rate_limit,
                          min(last_output["yaw"] + rate_limit, tvc_yaw_deg))
        last_output["pitch"] = tvc_pitch_deg
        last_output["yaw"] = tvc_yaw_deg

        return (tvc_pitch_deg, tvc_yaw_deg)

    return control_fn


def run_scenario(label, motor="e12", wind=(0,0,0), thrust_misalign=0.0,
                 mass_offset=(0,0,0), control_fn=None):
    """运行单场景仿真, 返回 summary dict"""
    sim = Rocket6DOF(
        motor_name=motor,
        wind=wind,
        thrust_misalign=thrust_misalign,
        mass_offset=mass_offset,
        control_fn=control_fn,
    )

    dt = 0.002
    max_alpha = 0.0  # 最大攻角
    max_omega = 0.0  # 最大角速度
    trajectory = []
    step_count = 0

    while sim.phase != "LAND" and sim.t < 120:
        sim.step(dt)
        step_count += 1
        # 记录攻角和角速度
        vel = sim.state[3:6]
        speed = np.linalg.norm(vel)
        if speed > 1.0:
            q = quat_normalize(sim.state[6:10])
            R_bw = quat_to_rotmat(q)
            vel_body = R_bw.T @ (vel / speed)
            alpha = math.atan2(math.sqrt(vel_body[1]**2 + vel_body[2]**2), vel_body[0])
            max_alpha = max(max_alpha, math.degrees(alpha))
            max_omega = max(max_omega, math.degrees(np.linalg.norm(sim.state[10:13])))

        # 数值稳定性检查
        if not np.isfinite(sim.state).all() or max_omega > 1e6:
            print(f"    [警告] 数值发散, 终止仿真 @ t={sim.t:.2f}s")
            break

        if step_count % 5 == 0:  # 10Hz 采样
            trajectory.append({
                "t": round(sim.t, 3),
                "x": round(float(sim.state[0]), 3),
                "y": round(float(sim.state[1]), 3),
                "z": round(float(sim.state[2]), 3),
                "speed": round(float(speed), 3),
                "alpha_max": round(max_alpha, 2),
                "phase": sim.phase,
            })

    summary = {
        "label": label,
        "max_altitude_m": round(max([p["z"] for p in trajectory] + [0]), 1),
        "flight_time_s": round(sim.t, 2),
        "landing_x": round(float(sim.state[0]), 2),
        "landing_y": round(float(sim.state[1]), 2),
        "max_attack_angle_deg": round(max_alpha, 2),
        "max_angular_rate_deg": round(max_omega, 2),
        "events": [{"t": round(e["t"],3), "event": e["event"]} for e in sim.events],
        "trajectory": trajectory,
    }
    return summary


def main():
    print("=" * 70)
    print("  Ad Astra 飞控算法仿真 (PID vs 开环)")
    print("=" * 70)

    # 双场景对比: 轻扰动 / 重扰动
    test_cases = [
        {
            "name": "轻扰动 (无风 + 0.3°推力偏斜 + 3mm CG偏心)",
            "wind": [0.0, 0, 0],
            "thrust_misalign": math.radians(0.3),
            "mass_offset": [0.003, 0.001, 0.0],
        },
        {
            "name": "重扰动 (5m/s东风 + 0.5°偏斜 + 5mm偏心)",
            "wind": [5.0, 0, 0],
            "thrust_misalign": math.radians(0.5),
            "mass_offset": [0.005, 0.002, 0.0],
        },
    ]

    all_results = []
    for tc in test_cases:
        print(f"\n{'='*70}")
        print(f"  场景: {tc['name']}")
        print(f"{'='*70}")

        scenarios = [
            ("开环 (无控制)", None),
            ("PID (Kp=3, Kd=0.8, Ki=0.3)", pid_controller(Kp=3.0, Kd=0.8)),
            ("PID (Kp=5, Kd=1.2, Ki=0.5)", pid_controller(Kp=5.0, Kd=1.2)),
        ]

        results = []
        for name, ctrl in scenarios:
            print(f"\n  [{name}]")
            out = run_scenario(name, wind=tc["wind"], thrust_misalign=tc["thrust_misalign"],
                               mass_offset=tc["mass_offset"], control_fn=ctrl)
            out["scenario"] = tc["name"]
            results.append(out)
            print(f"    顶点: {out['max_altitude_m']:.1f}m")
            print(f"    落点: x={out['landing_x']:.2f}m, y={out['landing_y']:.2f}m  (漂移 {math.hypot(out['landing_x'],out['landing_y']):.2f}m)")
            print(f"    最大攻角: {out['max_attack_angle_deg']:.2f}°")
            print(f"    最大角速度: {out['max_angular_rate_deg']:.2f}°/s")

        # 对比表
        print(f"\n  对比:")
        print(f"  {'控制器':<30s} {'顶点m':>7s} {'落点漂移m':>10s} {'攻角°':>8s} {'ω°/s':>8s}")
        print("  " + "-" * 70)
        for r in results:
            drift = math.hypot(r['landing_x'], r['landing_y'])
            print(f"  {r['label']:<30s} {r['max_altitude_m']:>7.1f} {drift:>10.2f} "
                  f"{r['max_attack_angle_deg']:>8.2f} {r['max_angular_rate_deg']:>8.2f}")

        all_results.extend(results)

    # 输出 JSON
    output = {
        "scenarios": all_results,
        "disturbances": [
            {
                "name": tc["name"],
                "wind_mps": tc["wind"],
                "thrust_misalign_deg": math.degrees(tc["thrust_misalign"]),
                "mass_offset_mm": [round(v*1000, 1) for v in tc["mass_offset"]],
            }
            for tc in test_cases
        ],
    }
    out_file = os.path.join(OUTPUT_DIR, "control_comparison.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[输出] {out_file}")


if __name__ == "__main__":
    main()
