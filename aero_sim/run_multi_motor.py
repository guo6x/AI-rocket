"""
多发动机对比仿真 (D12-5 / E12-6)
===============================
运行相同的火箭基体，分别使用不同发动机，输出各项关键指标用于验证是否满足 100m+ 高度及 15m/s 脱架速度。
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import font_config  # noqa: F401

sys.path.insert(0, os.path.dirname(__file__))

from rocketpy import Environment, SolidMotor, Rocket, Flight
from rocket_config import (
    NOSE_LENGTH, BODY_OUTER_RADIUS, FIN_COUNT, FIN_ROOT_CHORD, FIN_TIP_CHORD, 
    FIN_SPAN, FIN_SWEEP_LENGTH, FIN_POSITION_FROM_NOSE,
    MASS_DRY, TOTAL_LENGTH,
    RAIL_LENGTH, RAIL_INCLINATION, RAIL_HEADING,
    LAUNCH_LATITUDE, LAUNCH_LONGITUDE, LAUNCH_ELEVATION, CALIBER
)

# ── 不同发动机的参数 ──
MOTORS = {
    "C6-5": {
        "csv": "estes_c6_thrust.csv",
        "total_impulse": 8.8,
        "dry_mass": 0.014,
        "propellant_mass": 0.010,
        "burn_time": 1.9,
    },
    "D12-5": {
        "csv": "estes_d12_thrust.csv",
        "total_impulse": 20.0,
        "dry_mass": 0.0214,        # 45.6g 总重 - 24.2g 药
        "propellant_mass": 0.0242,
        "burn_time": 1.65,
    },
    "E12-6": {
        "csv": "estes_e12_thrust.csv",
        "total_impulse": 28.8,
        "dry_mass": 0.030,         # 估算值
        "propellant_mass": 0.0369, # ~36.9g 药
        "burn_time": 2.44,
    }
}


def run_multi_motor_sim():
    env = Environment(
        latitude=LAUNCH_LATITUDE,
        longitude=LAUNCH_LONGITUDE,
        elevation=LAUNCH_ELEVATION,
    )
    env.set_atmospheric_model(type="standard_atmosphere")

    results = {}

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Ad Astra 发动机升级对比仿真 (C6 vs D12 vs E12)', fontsize=14, fontweight='bold')
    
    colors = {"C6-5": "gray", "D12-5": "blue", "E12-6": "red"}

    print("=" * 60)
    print("  🚀 多发动机仿真开始运行...")
    print(f"  · 基线干重: {MASS_DRY*1000:.0f} g")
    print("=" * 60)

    for motor_name, specs in MOTORS.items():
        print(f"\n[运行] {motor_name}...")
        csv_path = os.path.join(os.path.dirname(__file__), specs['csv'])
        
        # 确保 CSV 存在（C6之前动态生成，现在如果不存在先退出）
        if not os.path.exists(csv_path) and motor_name == "C6-5":
            from run_simulation import create_thrust_curve_csv
            create_thrust_curve_csv()
            
        motor = SolidMotor(
            thrust_source=csv_path,
            dry_mass=specs["dry_mass"],
            dry_inertia=(0.0001, 0.0001, 0.00002),
            center_of_dry_mass_position=0.0,
            nozzle_radius=0.005,
            grain_number=1,
            grain_density=1700,
            grain_outer_radius=0.015,
            grain_initial_inner_radius=0.005,
            grain_initial_height=0.050,
            grain_separation=0.0,
            grains_center_of_mass_position=0.02,
            nozzle_position=0.0,
            burn_time=specs["burn_time"],
            throat_radius=0.004,
            interpolation_method="linear",
            coordinate_system_orientation="nozzle_to_combustion_chamber",
        )

        rocket = Rocket(
            radius=BODY_OUTER_RADIUS,
            mass=MASS_DRY,
            inertia=(0.005, 0.005, 0.0002),
            power_off_drag=0.5,
            power_on_drag=0.5,
            center_of_mass_without_motor=0,
            coordinate_system_orientation="tail_to_nose",
        )

        rocket.add_motor(motor, position=0)
        rocket.add_nose(length=NOSE_LENGTH, kind="Von Karman", position=TOTAL_LENGTH)
        rocket.add_trapezoidal_fins(
            n=FIN_COUNT, root_chord=FIN_ROOT_CHORD, tip_chord=FIN_TIP_CHORD,
            span=FIN_SPAN, sweep_length=FIN_SWEEP_LENGTH, 
            position=FIN_POSITION_FROM_NOSE - NOSE_LENGTH
        )
        rocket.add_tail(top_radius=BODY_OUTER_RADIUS, bottom_radius=BODY_OUTER_RADIUS * 0.9, length=0.01, position=0.01)

        flight = Flight(
            rocket=rocket, environment=env, rail_length=RAIL_LENGTH,
            inclination=RAIL_INCLINATION, heading=RAIL_HEADING,
            max_time=40, max_time_step=0.1, terminate_on_apogee=True
        )

        apogee = flight.apogee - LAUNCH_ELEVATION
        rail_v = flight.out_of_rail_velocity

        results[motor_name] = {"apogee": apogee, "rail_v": rail_v}

        print(f"  -> 远地点: {apogee:.1f} m  |  脱架速度: {rail_v:.2f} m/s")

        # 画图 - 高度
        t_alt = np.array(flight.altitude.source)
        if len(t_alt.shape) == 2:
            axes[0].plot(t_alt[:, 0], t_alt[:, 1] - LAUNCH_ELEVATION, color=colors[motor_name], 
                         label=f"{motor_name} (Apogee: {apogee:.1f}m)", linewidth=2)
        
        # 画图 - 速度
        t_vel = np.array(flight.speed.source)
        if len(t_vel.shape) == 2:
            axes[1].plot(t_vel[:, 0], t_vel[:, 1], color=colors[motor_name],
                         label=f"{motor_name} (Vmax: {flight.max_speed:.1f}m/s)", linewidth=2)

    # 图表装饰
    axes[0].set_title("飞行高度对比")
    axes[0].set_xlabel("时间 [s]")
    axes[0].set_ylabel("高度 (AGL) [m]")
    axes[0].axhline(y=100, color='g', linestyle='--', alpha=0.5, label='目标 100m')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_title("飞行速度对比")
    axes[1].set_xlabel("时间 [s]")
    axes[1].set_ylabel("速度 [m/s]")
    axes[1].axhline(y=15, color='orange', linestyle='--', alpha=0.5, label='安全脱架速度 15m/s')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join('results', 'multi_motor_comparison.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n[SAVED] {os.path.abspath(out_path)}")

    # 打印总结表
    print("\n" + "=" * 60)
    print("  📊 升级结果总结")
    print("=" * 60)
    print(f"  {'型号':<8} {'总冲(Ns)':<10} {'远地点(m)':<12} {'脱架速度(m/s)':<15}")
    for k, v in results.items():
        imp = MOTORS[k]['total_impulse']
        ap = v['apogee']
        rv = v['rail_v']
        
        # 判断
        ap_ok = "✅" if ap >= 100 else "❌"
        rv_ok = "✅" if rv >= 15 else "❌"
        
        print(f"  {k:<8} {imp:<10.1f} {ap:>7.1f} {ap_ok:<3} {rv:>10.2f} {rv_ok:<3}")

    print("=" * 60)

if __name__ == "__main__":
    run_multi_motor_sim()
