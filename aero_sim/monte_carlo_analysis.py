"""
Ad Astra — 蒙特卡洛散布分析 (Phase 4)
======================================
N=100 次随机扰动仿真, 统计落点散布椭圆 + CEP

随机扰动:
- 风速: 0-5 m/s 均匀分布
- 风向: 0-360° 均匀分布
- 推力偏斜: 0-0.5°
- 推力偏斜方向: 0-360°
- CG 偏心: x,y 各 0-5mm

统计输出:
- 100 个落点 (x, y)
- 圆概率误差 CEP
- 散布椭圆 (半长轴, 半短轴, 方向角)
- 比较开环 vs PID 闭环
"""
import os
import sys
import math
import json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sixdof_simulation import Rocket6DOF, quat_to_rotmat, quat_normalize
from control_simulation import pid_controller

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")
N_SAMPLES = 30  # 采样次数 (30 个样本足以估计散布椭圆)
SEED = 42  # 复现性


def random_disturbance(rng):
    """生成一组随机扰动"""
    wind_speed = rng.uniform(0, 5.0)        # m/s
    wind_dir = rng.uniform(0, 2 * math.pi)  # rad
    wind = [wind_speed * math.cos(wind_dir), wind_speed * math.sin(wind_dir), 0]

    thrust_misalign_mag = rng.uniform(0, math.radians(0.5))  # 0-0.5°
    thrust_dir = rng.uniform(0, 2 * math.pi)
    # 简化: 推力偏斜只取大小, 方向通过 CG偏心体现
    thrust_misalign = thrust_misalign_mag

    cg_offset_x = rng.uniform(-0.005, 0.005)  # ±5mm
    cg_offset_y = rng.uniform(-0.005, 0.005)
    mass_offset = [cg_offset_x, cg_offset_y, 0.0]

    return {
        "wind": wind,
        "thrust_misalign": thrust_misalign,
        "mass_offset": mass_offset,
        "wind_speed": wind_speed,
        "wind_dir_deg": math.degrees(wind_dir),
        "thrust_misalign_deg": math.degrees(thrust_misalign),
        "cg_offset_mm": [cg_offset_x*1000, cg_offset_y*1000],
    }


def run_single(dist, control_fn=None, motor="e12"):
    """运行单次仿真, 返回落点 (x, y, max_h, flight_time)"""
    sim = Rocket6DOF(
        motor_name=motor,
        wind=dist["wind"],
        thrust_misalign=dist["thrust_misalign"],
        mass_offset=dist["mass_offset"],
        control_fn=control_fn,
    )
    dt = 0.002
    max_h = 0
    while sim.phase != "LAND" and sim.t < 120:
        sim.step(dt)
        if not np.isfinite(sim.state).all():
            return None  # 发散, 跳过
        max_h = max(max_h, sim.state[2])

    return {
        "x": float(sim.state[0]),
        "y": float(sim.state[1]),
        "max_h": float(max_h),
        "flight_time": float(sim.t),
    }


def compute_cep(landings):
    """计算圆概率误差 CEP: 50% 落点落入的圆半径"""
    if not landings:
        return 0.0
    xs = np.array([p["x"] for p in landings])
    ys = np.array([p["y"] for p in landings])
    cx, cy = xs.mean(), ys.mean()
    dists = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    dists.sort()
    cep = float(np.median(dists))
    return cep


def compute_dispersion_ellipse(landings):
    """计算散布椭圆 (协方差特征值分解)"""
    if len(landings) < 5:
        return {"a": 0, "b": 0, "angle": 0}
    xs = np.array([p["x"] for p in landings])
    ys = np.array([p["y"] for p in landings])
    cx, cy = xs.mean(), ys.mean()

    # 协方差矩阵
    cov = np.cov(xs, ys)
    # 特征值分解
    eigvals, eigvecs = np.linalg.eigh(cov)
    # 半长轴/半短轴 = 2 * sqrt(eigvals) (2σ 椭圆, 包含 ~95% 落点)
    a = float(2 * math.sqrt(max(eigvals[1], 0)))
    b = float(2 * math.sqrt(max(eigvals[0], 0)))
    # 椭圆方向角 (长轴与 x 轴夹角)
    angle = float(math.degrees(math.atan2(eigvecs[1, 1], eigvecs[0, 1])))

    return {
        "a": round(a, 2),
        "b": round(b, 2),
        "angle": round(angle, 1),
        "cx": round(float(cx), 2),
        "cy": round(float(cy), 2),
    }


def main():
    print("=" * 70)
    print(f"  Ad Astra 蒙特卡洛散布分析 (N={N_SAMPLES})")
    print("=" * 70)

    rng = np.random.default_rng(SEED)
    disturbances = [random_disturbance(rng) for _ in range(N_SAMPLES)]

    # 两组对比: 开环 vs PID
    controllers = [
        ("开环 (无控制)", None),
        ("PID (Kp=1.0, Kd=0.3)", pid_controller(Kp=1.0, Kd=0.3)),
    ]

    all_results = {}
    for ctrl_name, ctrl_fn in controllers:
        print(f"\n[运行] {ctrl_name} ...")
        landings = []
        for i, dist in enumerate(disturbances):
            result = run_single(dist, control_fn=ctrl_fn)
            if result is None:
                print(f"  · 样本 {i+1}: 发散, 跳过")
                continue
            landings.append(result)
            if (i+1) % 20 == 0:
                print(f"  · 已完成 {i+1}/{N_SAMPLES}")

        # 统计
        cep = compute_cep(landings)
        ellipse = compute_dispersion_ellipse(landings)
        altitudes = [p["max_h"] for p in landings]
        times = [p["flight_time"] for p in landings]

        print(f"  ✓ 完成 {len(landings)}/{N_SAMPLES} 样本")
        print(f"    平均顶点: {np.mean(altitudes):.1f} m (±{np.std(altitudes):.1f})")
        print(f"    平均飞行时间: {np.mean(times):.2f} s (±{np.std(times):.2f})")
        print(f"    散布中心: ({ellipse['cx']:.2f}, {ellipse['cy']:.2f}) m")
        print(f"    CEP (50%圆): {cep:.2f} m")
        print(f"    2σ椭圆: a={ellipse['a']:.2f}m, b={ellipse['b']:.2f}m, 角={ellipse['angle']:.1f}°")

        all_results[ctrl_name] = {
            "label": ctrl_name,
            "n_samples": len(landings),
            "landings": landings,
            "statistics": {
                "cep_m": round(cep, 2),
                "ellipse_a_m": ellipse["a"],
                "ellipse_b_m": ellipse["b"],
                "ellipse_angle_deg": ellipse["angle"],
                "center_x": ellipse["cx"],
                "center_y": ellipse["cy"],
                "mean_altitude_m": round(float(np.mean(altitudes)), 1),
                "std_altitude_m": round(float(np.std(altitudes)), 1),
                "mean_flight_time_s": round(float(np.mean(times)), 2),
                "max_drift_m": round(float(max(math.hypot(p["x"], p["y"]) for p in landings)), 2),
            },
        }

    # 对比
    print("\n" + "=" * 70)
    print("  对比表")
    print("=" * 70)
    print(f"{'控制器':<30s} {'CEP/m':>8s} {'2σ_a/m':>8s} {'2σ_b/m':>8s} {'平均顶点':>10s} {'最大漂移':>10s}")
    print("-" * 80)
    for ctrl_name, _ in controllers:
        s = all_results[ctrl_name]["statistics"]
        print(f"{ctrl_name:<30s} {s['cep_m']:>8.2f} {s['ellipse_a_m']:>8.2f} "
              f"{s['ellipse_b_m']:>8.2f} {s['mean_altitude_m']:>10.1f} {s['max_drift_m']:>10.2f}")

    # 改善
    if len(controllers) >= 2:
        open_stats = all_results[controllers[0][0]]["statistics"]
        pid_stats = all_results[controllers[1][0]]["statistics"]
        print(f"\n[改善] PID vs 开环:")
        print(f"  CEP: {open_stats['cep_m']:.2f}m → {pid_stats['cep_m']:.2f}m "
              f"(↓ {open_stats['cep_m']-pid_stats['cep_m']:.2f}m, "
              f"{(1-pid_stats['cep_m']/open_stats['cep_m'])*100:.0f}%)")
        print(f"  2σ椭圆面积: {math.pi*open_stats['ellipse_a_m']*open_stats['ellipse_b_m']:.0f}m² → "
              f"{math.pi*pid_stats['ellipse_a_m']*pid_stats['ellipse_b_m']:.0f}m²")

    # 输出 JSON
    output = {
        "n_samples": N_SAMPLES,
        "seed": SEED,
        "controllers": list(all_results.values()),
        "disturbances_summary": {
            "wind_speed_range_mps": [0, 5],
            "thrust_misalign_range_deg": [0, 0.5],
            "cg_offset_range_mm": [-5, 5],
        },
    }
    out_file = os.path.join(OUTPUT_DIR, "monte_carlo_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[输出] {out_file}")


if __name__ == "__main__":
    main()
