"""
Ad Astra 探空火箭 — 飞行弹道仿真（RocketPy 6-DOF）
=====================================================
使用 RocketPy 库构建完整火箭模型并运行 6-DOF 弹道仿真。
输出：弹道曲线、速度曲线、飞行事件摘要。
"""

import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无头模式，直接保存图片
import matplotlib.pyplot as plt
import font_config  # noqa: F401 — 中文字体配置

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(__file__))

from rocket_config import (
    NOSE_TYPE, NOSE_LENGTH, NOSE_BASE_RADIUS,
    BODY_OUTER_RADIUS, BODY_INNER_RADIUS, BODY_LENGTH,
    FIN_COUNT, FIN_ROOT_CHORD, FIN_TIP_CHORD, FIN_SPAN,
    FIN_SWEEP_LENGTH, FIN_THICKNESS, FIN_POSITION_FROM_NOSE,
    MASS_DRY, MASS_TOTAL, TOTAL_LENGTH, CALIBER,
    MOTOR_TOTAL_IMPULSE, MOTOR_BURN_TIME, MOTOR_AVG_THRUST,
    MOTOR_DRY_MASS, MOTOR_PROPELLANT_MASS,
    RAIL_LENGTH, RAIL_INCLINATION, RAIL_HEADING,
    LAUNCH_LATITUDE, LAUNCH_LONGITUDE, LAUNCH_ELEVATION,
)


# C6-5 的推力生成函数保留但不再默认调用
def create_thrust_curve_csv():
    # ...
    pass


def run_rocketpy_simulation():
    """使用 RocketPy 执行完整 6-DOF 仿真"""
    try:
        from rocketpy import Environment, SolidMotor, Rocket, Flight
    except ImportError:
        print("[ERR] RocketPy not installed! Run: py -m pip install rocketpy")
        sys.exit(1)

    print("=" * 60)
    print("  Ad Astra 探空火箭 — 6-DOF 飞行弹道仿真")
    print("=" * 60)

    # ── 1. 环境 ──
    print("\n[1/4] 设置发射环境...")
    env = Environment(
        latitude=LAUNCH_LATITUDE,
        longitude=LAUNCH_LONGITUDE,
        elevation=LAUNCH_ELEVATION,
    )
    # 使用标准大气模型（无需联网）
    env.set_atmospheric_model(type="standard_atmosphere")
    print(f"  · 发射点: ({LAUNCH_LATITUDE}°N, {LAUNCH_LONGITUDE}°E), "
          f"海拔 {LAUNCH_ELEVATION}m")

    # ── 2. 发动机 ──
    print("\n[2/4] 定义固体发动机 (Estes D12-5)...")
    thrust_csv = os.path.join(os.path.dirname(__file__), 'estes_d12_thrust.csv')

    # 动态匹配药柱尺寸（防止 RocketPy 计算出现负质量或极低比冲导致 NaN 挂起）
    grain_density = 1700
    grain_outer_radius = 0.012
    grain_initial_inner_radius = 0.004
    grain_volume = MOTOR_PROPELLANT_MASS / grain_density
    grain_initial_height = grain_volume / (math.pi * (grain_outer_radius**2 - grain_initial_inner_radius**2))

    motor = SolidMotor(
        thrust_source=thrust_csv,
        dry_mass=MOTOR_DRY_MASS,
        dry_inertia=(0.0001, 0.0001, 0.00002),  # 近似值
        center_of_dry_mass_position=0.0,  # 相对于发动机喷管
        nozzle_radius=0.005,              # 喷管半径 5mm
        grain_number=1,
        grain_density=grain_density,
        grain_outer_radius=grain_outer_radius,
        grain_initial_inner_radius=grain_initial_inner_radius,
        grain_initial_height=grain_initial_height,
        grain_separation=0.0,             # 药柱间距 (单药柱为0)
        grains_center_of_mass_position=0.02,
        nozzle_position=0.0,
        burn_time=MOTOR_BURN_TIME,
        throat_radius=0.004,              # 喉部半径 4mm
        interpolation_method="linear",
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )
    print(f"  [OK] {MOTOR_TOTAL_IMPULSE} N*s")
    print(f"  [OK] {MOTOR_AVG_THRUST:.1f} N")
    print(f"  [OK] {MOTOR_BURN_TIME} s")

    # ── 3. 火箭 ──
    print("\n[3/4] 构建火箭模型...")

    # 干重中减去发动机壳体（RocketPy 会自己处理发动机质量）
    rocket_dry_mass = MASS_DRY

    rocket = Rocket(
        radius=BODY_OUTER_RADIUS,
        mass=rocket_dry_mass,
        inertia=(
            0.005,   # I11 横向惯性矩 (近似) [kg·m²]
            0.005,   # I22
            0.0002,  # I33 纵轴惯性矩
        ),
        power_off_drag="poweroff_drag.csv" if os.path.exists("poweroff_drag.csv") else 0.5,
        power_on_drag="poweron_drag.csv" if os.path.exists("poweron_drag.csv") else 0.5,
        center_of_mass_without_motor=0,  # 暂设为坐标原点，后续调整
        coordinate_system_orientation="tail_to_nose",
    )

    # 安装发动机（位于管底）
    rocket.add_motor(motor, position=0)   # 0 = 管底（tail 端）

    # 添加整流罩
    rocket.add_nose(
        length=NOSE_LENGTH,
        kind="Von Karman",
        position=TOTAL_LENGTH,  # 头锥顶端
    )

    # 添加尾翼
    rocket.add_trapezoidal_fins(
        n=FIN_COUNT,
        root_chord=FIN_ROOT_CHORD,
        tip_chord=FIN_TIP_CHORD,
        span=FIN_SPAN,
        sweep_length=FIN_SWEEP_LENGTH,
        position=FIN_POSITION_FROM_NOSE - NOSE_LENGTH,  # 转换到 tail_to_nose 坐标系
    )

    # 添加尾部（管底封盖）
    rocket.add_tail(
        top_radius=BODY_OUTER_RADIUS,
        bottom_radius=BODY_OUTER_RADIUS * 0.9,
        length=0.01,
        position=0.01,
    )

    # 注意：暂不添加降落伞（会导致仿真求解器挂起）
    # 后续可通过 rocket.add_parachute() 添加

    print(f"  [OK] {TOTAL_LENGTH*1000:.0f} mm")
    print(f"  [OK] {rocket_dry_mass*1000:.0f} g")
    print(f"  [OK] {FIN_COUNT} pcs")

    # ── 4. 飞行仿真 ──
    print("\n[4/4] 运行 6-DOF 弹道仿真...")

    flight = Flight(
        rocket=rocket,
        environment=env,
        rail_length=RAIL_LENGTH,
        inclination=RAIL_INCLINATION,
        heading=RAIL_HEADING,
        max_time=60,         # 最大仿真时间 60s (防挂起)
        max_time_step=0.05,  # 最大时间步长
        terminate_on_apogee=True,  # 到达远地点后终止
    )

    # ── 输出关键数据 ──
    print("\n" + "=" * 60)
    print("  [RESULT] Simulation Summary")
    print("=" * 60)

    apogee = flight.apogee - LAUNCH_ELEVATION
    print(f"  [APOGEE]  {apogee:.1f} m")
    print(f"  [TIME]    {flight.apogee_time:.2f} s")
    print(f"  [RAIL]    {flight.out_of_rail_velocity:.2f} m/s")
    print(f"  [VMAX]    {flight.max_speed:.2f} m/s")
    print(f"  [MACH]    {flight.max_mach_number:.3f}")
    print(f"  [ACCEL]   {flight.max_acceleration:.2f} m/s2")
    print(f"  [TFINAL]  {flight.t_final:.1f} s")

    # 安全检查
    print(f"\n{'─' * 60}")
    if flight.out_of_rail_velocity < 15:
        print("  [WARN] 警告: 脱架速度 < 15 m/s, 风稳定性不足!")
        print("     -> 建议: 使用更长导轨或更大推力发动机")
    else:
        print("  [OK] 脱架速度合格 (>= 15 m/s)")

    if flight.max_mach_number > 0.8:
        print("  [WARN] 接近跨声速区域, 阻力系数会急剧增加")
    else:
        print("  [OK] 全程亚声速飞行, 阻力模型可靠")

    print("=" * 60)

    # ── 绘图 ──
    plot_results(flight, apogee)

    return flight


def plot_results(flight, apogee):
    """生成弹道仿真结果图表"""
    os.makedirs('results', exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f'Ad Astra 探空火箭 — 弹道仿真结果 (D12-5)\n'
        f'最大高度: {apogee:.1f}m | 最大马赫: {flight.max_mach_number:.3f} | 脱架速度: {flight.out_of_rail_velocity:.1f}m/s',
        fontsize=14, fontweight='bold'
    )

    # 1. 高度 vs 时间
    ax = axes[0, 0]
    t = np.array(flight.altitude.source)
    if len(t.shape) == 2:
        ax.plot(t[:, 0], t[:, 1] - LAUNCH_ELEVATION, 'b-', linewidth=2)
    ax.set_xlabel('时间 [s]')
    ax.set_ylabel('高度 AGL [m]')
    ax.set_title('飞行高度')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=apogee, color='r', linestyle='--', alpha=0.5, label=f'远地点 {apogee:.1f}m')
    ax.legend()

    # 2. 速度 vs 时间
    ax = axes[0, 1]
    t = np.array(flight.speed.source)
    if len(t.shape) == 2:
        ax.plot(t[:, 0], t[:, 1], 'r-', linewidth=2)
    ax.set_xlabel('时间 [s]')
    ax.set_ylabel('速度 [m/s]')
    ax.set_title('飞行速度')
    ax.grid(True, alpha=0.3)

    # 3. 马赫数 vs 时间
    ax = axes[1, 0]
    t = np.array(flight.mach_number.source)
    if len(t.shape) == 2:
        ax.plot(t[:, 0], t[:, 1], 'g-', linewidth=2)
    ax.set_xlabel('时间 [s]')
    ax.set_ylabel('马赫数')
    ax.set_title('马赫数')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0.3, color='orange', linestyle='--', alpha=0.5, label='Ma=0.3 可压缩性')
    ax.legend()

    # 4. 加速度 vs 时间
    ax = axes[1, 1]
    t = np.array(flight.acceleration.source)
    if len(t.shape) == 2:
        ax.plot(t[:, 0], t[:, 1], 'm-', linewidth=2)
    ax.set_xlabel('时间 [s]')
    ax.set_ylabel('加速度 [m/s²]')
    ax.set_title('加速度')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join('results', 'trajectory_simulation.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n[SAVED] {os.path.abspath(out_path)}")
    plt.close(fig)


# ═══════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    flight = run_rocketpy_simulation()
