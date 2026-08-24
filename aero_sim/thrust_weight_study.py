"""
Ad Astra — 推重比攻关 (Phase 1)
================================
四方案对比: C6-5基线 / D12 / E12 / 砍重150g(C6-5)
输出: 控制台对比表 + JSON 给后续 HTML 看板使用
所有参数严格对齐 rocket_config.py
"""
import os
import sys
import math
import json
import csv
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from rocket_config import (
    MASS_DRY, MOTOR_DRY_MASS, MOTOR_PROPELLANT_MASS,
    RAIL_LENGTH, BODY_OUTER_RADIUS, TOTAL_LENGTH,
)

G = 9.81
RAIL_LEN = RAIL_LENGTH            # 1.0 m
V_RAIL_SAFE = 15.0                # m/s, 安全脱架速度下限
DRAG_CD = 0.45                    # 低速段保守阻力系数
ROCKET_AREA = math.pi * BODY_OUTER_RADIUS ** 2  # 横截面积
RHO_0 = 1.225                     # 海平面空气密度

AERO_DIR = os.path.dirname(__file__)
OUTPUT_JSON = os.path.join(AERO_DIR, "results", "thrust_weight_study.json")
os.makedirs(os.path.join(AERO_DIR, "results"), exist_ok=True)


def load_thrust_curve(name):
    """加载 thrust csv, 返回 (t_array, F_array)"""
    path = os.path.join(AERO_DIR, f"estes_{name}_thrust.csv")
    ts, fs = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                try:
                    t = float(row[0]); F = float(row[1])
                    ts.append(t); fs.append(F)
                except ValueError:
                    continue
    return np.array(ts), np.array(fs)


def integrate_burn(t_arr, F_arr, m0, mp):
    """燃烧段积分: 返回 (v_burnout, h_burnout, t_burnout, m_burnout)
    使用 RK4 + 简化阻力 + 质量线性减少"""
    dt = 0.001
    t_end = t_arr[-1]
    t = 0.0
    v = 0.0
    h = 0.0
    m = m0
    mdot = mp / t_end  # 推进剂质量流量

    while t < t_end - 1e-9:
        # 当前推力 (线性插值)
        F = float(np.interp(t, t_arr, F_arr))
        # 阻力
        rho = RHO_0 * math.exp(-h / 8500.0)
        q = 0.5 * rho * v * v * ROCKET_AREA * DRAG_CD
        # 加速度
        def accel(ht, vt, mt, Ft):
            qd = 0.5 * RHO_0 * math.exp(-ht / 8500.0) * vt * vt * ROCKET_AREA * DRAG_CD
            return (Ft - qd - mt * G) / mt

        a1 = accel(h, v, m, F)
        # RK4 简化
        v2 = v + 0.5 * dt * a1; h2 = h + 0.5 * dt * v; m2 = m - 0.5 * dt * mdot
        a2 = accel(h2, v2, m2, F)
        v3 = v + 0.5 * dt * a2; h3 = h + 0.5 * dt * v2; m3 = m - 0.5 * dt * mdot
        a3 = accel(h3, v3, m3, F)
        v4 = v + dt * a3; h4 = h + dt * v3; m4 = m - dt * mdot
        a4 = accel(h4, v4, m4, F)

        v += (dt / 6.0) * (a1 + 2 * a2 + 2 * a3 + a4)
        h += (dt / 6.0) * (v + 2 * v2 + 2 * v3 + v4) * 0.5  # 平均速度
        m -= dt * mdot
        t += dt

    return v, h, t_end, m


def coast_to_apogee(v0, h0, m_dry):
    """惯性飞行至顶点 (无推力, 含阻力)"""
    dt = 0.01
    v, h, t = v0, h0, 0.0
    while v > 0 and t < 60:
        rho = RHO_0 * math.exp(-h / 8500.0)
        q = 0.5 * rho * v * v * ROCKET_AREA * DRAG_CD
        a = -(q + m_dry * G) / m_dry
        v += a * dt
        h += v * dt
        t += dt
    return h, t


def rail_exit_velocity(t_arr, F_arr, m0, mp):
    """脱架速度: 火箭在导轨上滑行1m, 推力积分到出架时刻
    火箭在导轨上时若推力<重力则保持静止(被导轨挡住), 不算"推力不足退出"
    只有当燃烧结束仍未脱离导轨才算失败"""
    dt = 0.001
    t = 0.0
    v = 0.0
    h = 0.0
    t_end = t_arr[-1]
    mdot = mp / t_end

    while h < RAIL_LEN and t < t_end:
        F = float(np.interp(t, t_arr, F_arr))
        a = (F - m0 * G) / m0
        # 推力<重力时火箭被导轨挡住, 不上升也不后退
        if a < 0 and h < 1e-6:
            v = 0.0
            h = 0.0
        else:
            v += a * dt
            h += v * dt
            if h < 0:
                h = 0.0; v = 0.0
        t += dt
        m0 -= dt * mdot  # 推进剂持续消耗
    return v, t, h >= RAIL_LEN


def run_case(name, motor_name, mass_dry_override=None):
    """运行单方案"""
    t_arr, F_arr = load_thrust_curve(motor_name)
    F_avg = float(np.trapz(F_arr, t_arr) / t_arr[-1])
    F_peak = float(F_arr.max())
    total_impulse = float(np.trapz(F_arr, t_arr))
    burn_time = float(t_arr[-1])

    m_dry = mass_dry_override if mass_dry_override else MASS_DRY
    m_prop = MOTOR_PROPELLANT_MASS
    m0 = m_dry + MOTOR_DRY_MASS + m_prop  # 起飞质量
    m_burnout = m_dry + MOTOR_DRY_MASS    # 燃尽质量

    twr = F_avg / (m0 * G)
    v_rail, t_rail, ok = rail_exit_velocity(t_arr, F_arr, m0, m_prop)
    v_burn, h_burn, t_burn, _ = integrate_burn(t_arr, F_arr, m0, m_prop)
    h_apogee, t_coast = coast_to_apogee(v_burn, h_burn, m_burnout)
    h_apogee_total = h_burn + h_apogee
    t_apogee_total = t_burn + t_coast

    safe = "✅ 安全" if v_rail >= V_RAIL_SAFE else "❌ 不安全"
    verdict = ""
    if v_rail < 8:
        verdict = "推力严重不足, 风标效应致乱飞"
    elif v_rail < V_RAIL_SAFE:
        verdict = f"脱架速度不足, 需+{(V_RAIL_SAFE-v_rail):.1f}m/s"
    else:
        verdict = "可稳定起飞"

    return {
        "name": name,
        "motor": motor_name.upper(),
        "mass_dry_g": round(m_dry * 1000, 1),
        "mass_takeoff_g": round(m0 * 1000, 1),
        "total_impulse_Ns": round(total_impulse, 2),
        "avg_thrust_N": round(F_avg, 2),
        "peak_thrust_N": round(F_peak, 2),
        "burn_time_s": round(burn_time, 2),
        "TWR": round(twr, 2),
        "v_rail_mps": round(v_rail, 2),
        "rail_exit_time_s": round(t_rail, 2),
        "v_burnout_mps": round(v_burn, 2),
        "h_burnout_m": round(h_burn, 1),
        "h_apogee_m": round(h_apogee_total, 1),
        "t_apogee_s": round(t_apogee_total, 2),
        "safe": bool(v_rail >= V_RAIL_SAFE),
        "verdict": verdict,
    }


def main():
    print("=" * 80)
    print("  Ad Astra 推重比攻关 — 四方案对比 (C6-5 / D12 / E12 / 砍重150g)")
    print("=" * 80)
    print(f"  基线干重: {MASS_DRY*1000:.0f} g  |  导轨长度: {RAIL_LEN} m  |  安全脱架: ≥{V_RAIL_SAFE} m/s")
    print()

    cases = [
        run_case("基线 C6-5", "c6"),
        run_case("升级 D12", "d12"),
        run_case("升级 E12", "e12"),
        run_case("砍重150g + C6-5", "c6", mass_dry_override=0.150),
    ]

    # 打印对比表
    headers = ["方案", "发动机", "干重g", "起飞g", "TWR", "v脱架", "v燃尽", "h顶点m", "t顶点s", "判定"]
    rows = []
    for c in cases:
        rows.append([
            c["name"], c["motor"], c["mass_dry_g"], c["mass_takeoff_g"],
            f"{c['TWR']:.2f}", f"{c['v_rail_mps']:.1f}", f"{c['v_burnout_mps']:.1f}",
            f"{c['h_apogee_m']:.0f}", f"{c['t_apogee_s']:.1f}",
            "✅" if c["safe"] else "❌"
        ])

    # 列宽
    widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("-" * (sum(widths) + 2 * (len(widths) - 1)))
    for r in rows:
        print(fmt.format(*r))

    print()
    print("[结论]")
    for c in cases:
        print(f"  · {c['name']:18s} → {c['verdict']}")

    # 选最优
    safe_cases = [c for c in cases if c["safe"]]
    if safe_cases:
        best = max(safe_cases, key=lambda c: c["h_apogee_m"])
        print(f"\n[推荐] {best['name']} → 顶点 {best['h_apogee_m']:.0f}m, TWR={best['TWR']}")
    else:
        # 都不安全, 选脱架速度最高的
        best = max(cases, key=lambda c: c["v_rail_mps"])
        print(f"\n[警告] 无方案达到安全脱架速度, 最接近: {best['name']} (v脱架={best['v_rail_mps']:.1f}m/s)")

    # 保存 JSON
    output = {
        "baseline_mass_g": round(MASS_DRY * 1000, 1),
        "rail_length_m": RAIL_LEN,
        "v_rail_safe_mps": V_RAIL_SAFE,
        "cases": cases,
        "recommended": best["name"],
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[输出] {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
