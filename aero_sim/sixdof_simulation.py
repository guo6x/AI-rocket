"""
Ad Astra — 自研 6DOF 刚体飞行仿真 (Phase 2)
=============================================
状态向量 (13维): [x,y,z, vx,vy,vz, q0,q1,q2,q3, wx,wy,wz]
- 位置/速度: ENU 东北天坐标系
- 姿态: 四元数 (body 相对 world)
- 角速度: body frame

飞行阶段: RAIL(导轨) → BURN(燃烧) → COAST(惯性) → APOGEE(开伞) → DESCENT(下降) → LAND

基准方案: E12 发动机 (v脱架 11.3 m/s, 顶点 150m)
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
    BODY_OUTER_RADIUS, BODY_LENGTH, TOTAL_LENGTH,
    NOSE_LENGTH, FIN_SPAN,
    RAIL_LENGTH, RAIL_INCLINATION,
)

G = 9.81
RHO_0 = 1.225
SCALE_HEIGHT = 8500.0
RA = BODY_OUTER_RADIUS  # 0.0375
ROCKET_AREA = math.pi * RA ** 2
CD_BODY = 0.45            # 亚声速阻力系数
CD_DROGUE = 0.8           # 减速伞
CD_MAIN = 1.5             # 主伞
DROGUE_AREA = 0.05        # m² (20cm 减速伞)
MAIN_AREA = 0.5           # m² (80cm 主伞)
PARACHUTE_MASS = 0.030    # kg

# 转动惯量 (近似为均质圆柱)
I_XX = 0.5 * (MASS_DRY + MOTOR_PROPELLANT_MASS) * RA ** 2  # 滚转
I_YY = I_ZZ = (1/12) * (MASS_DRY + MOTOR_PROPELLANT_MASS) * TOTAL_LENGTH ** 2  # 俯仰/偏航

# CP-CG 静稳定裕度 (来自 aero-sim-report.md: 1.36 caliber)
STABILITY_CALIBER = 1.36
CP_CG_OFFSET = STABILITY_CALIBER * 2 * RA  # 102mm, CP 在 CG 后方

AERO_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(AERO_DIR, "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_thrust_curve(name):
    path = os.path.join(AERO_DIR, f"estes_{name}_thrust.csv")
    ts, fs = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                try:
                    ts.append(float(row[0])); fs.append(float(row[1]))
                except ValueError:
                    continue
    return np.array(ts), np.array(fs)


def quat_mul(q1, q2):
    """四元数乘法 (Hamilton convention)"""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])


def quat_normalize(q):
    n = np.linalg.norm(q)
    if n < 1e-12:
        return np.array([1.0, 0, 0, 0])
    return q / n


def quat_to_rotmat(q):
    """四元数 → 旋转矩阵 (body → world)"""
    w, x, y, z = q
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - w*z),     2*(x*z + w*y)],
        [2*(x*y + w*z),     1 - 2*(x*x + z*z), 2*(y*z - w*x)],
        [2*(x*z - w*y),     2*(y*z + w*x),     1 - 2*(x*x + y*y)],
    ])


def quat_from_axis_angle(axis, angle):
    """轴角 → 四元数"""
    axis = np.asarray(axis, dtype=float)
    n = np.linalg.norm(axis)
    if n < 1e-12:
        return np.array([1.0, 0, 0, 0])
    axis = axis / n
    s = math.sin(angle / 2)
    return np.array([math.cos(angle / 2), axis[0]*s, axis[1]*s, axis[2]*s])


def air_density(h):
    """ISA 简化大气模型"""
    if h < 0:
        h = 0
    return RHO_0 * math.exp(-h / SCALE_HEIGHT)


class Rocket6DOF:
    """6DOF 刚体火箭仿真"""
    def __init__(self, motor_name="e12", wind=[0,0,0], thrust_misalign=0.0,
                 mass_offset=[0,0,0], control_fn=None):
        self.t_arr, self.F_arr = load_thrust_curve(motor_name)
        self.t_burn = float(self.t_arr[-1])
        self.motor_name = motor_name
        self.wind = np.array(wind, dtype=float)  # ENU 风速 m/s
        self.thrust_misalign = thrust_misalign   # rad, 推力偏斜角
        self.mass_offset = np.array(mass_offset, dtype=float)  # m, CG偏心
        self.control_fn = control_fn  # 控制律回调 (t, state) → (tvc_pitch, tvc_yaw) deg

        # 初始状态: 在导轨上, 仰角 85° (近乎垂直, 略前倾)
        # 箭体 +x_body 在 world 中指向 [cos(85°), 0, sin(85°)]
        # 需要绕 y 轴 (北) 旋转 -85°
        rail_elev = math.radians(RAIL_INCLINATION)  # 85°
        q_init = quat_from_axis_angle([0, 1, 0], -rail_elev)  # 绕 y 轴旋转 -85°

        # 状态: [x,y,z, vx,vy,vz, q0,q1,q2,q3, wx,wy,wz]
        self.state = np.zeros(13)
        self.state[6:10] = q_init
        self.t = 0.0
        self.phase = "RAIL"
        self.events = []
        self.drogue_deployed = False
        self.main_deployed = False

        # 推进剂质量
        self.m_prop = MOTOR_PROPELLANT_MASS
        self.mdot = MOTOR_PROPELLANT_MASS / self.t_burn

    @property
    def mass(self):
        m_dry_total = MASS_DRY + MOTOR_DRY_MASS
        if self.t < self.t_burn:
            return m_dry_total + self.m_prop - self.mdot * self.t
        return m_dry_total + (PARACHUTE_MASS if self.drogue_deployed else 0)

    @property
    def thrust(self):
        if self.t > self.t_burn:
            return 0.0
        return float(np.interp(self.t, self.t_arr, self.F_arr))

    def derivatives(self, t, state, control_input=(0.0, 0.0)):
        """计算状态导数 (13维)"""
        pos = state[0:3]
        vel = state[3:6]
        q = quat_normalize(state[6:10])
        omega = state[10:13]  # body frame 角速度

        m = self.mass
        R_bw = quat_to_rotmat(q)  # body→world
        R_wb = R_bw.T              # world→body

        # 速度 (相对空气)
        v_air_world = vel - np.array([self.wind[0], self.wind[1], 0])  # 风只在水平面
        v_air_body = R_wb @ v_air_world
        speed = np.linalg.norm(v_air_world)

        # === 力 (body frame) ===
        # 1. 推力 (沿 +x_body, 含推力偏斜和 TVC)
        F_thrust_mag = self.thrust
        tvc_pitch, tvc_yaw = control_input
        # 推力方向: 主轴 + 小偏斜 (推力偏斜 + TVC)
        alpha = self.thrust_misalign + math.radians(tvc_pitch)
        beta = math.radians(tvc_yaw)
        F_thrust_body = F_thrust_mag * np.array([
            math.cos(alpha) * math.cos(beta),
            math.sin(alpha),
            math.sin(beta),
        ])

        # 2. 重力 (world → body)
        F_grav_world = np.array([0, 0, -m * G])
        F_grav_body = R_wb @ F_grav_world

        # 3. 气动阻力 (body frame, 沿 -v_air_body)
        rho = air_density(pos[2])
        F_aero_body = np.zeros(3)
        if speed > 0.1:
            # 轴向阻力 (压差阻力) + 法向阻力 (侧滑产生的法向力, 稳定力矩的力源)
            v_axial = v_air_body[0]  # 沿箭体轴速度
            v_normal = v_air_body[1:3]  # 侧滑速度
            # 轴向阻力
            F_aero_body[0] = -0.5 * rho * v_axial * abs(v_axial) * ROCKET_AREA * CD_BODY
            # 法向力 (尾翼+箭体) - 这是静稳定的关键
            v_n_mag = np.linalg.norm(v_normal)
            if v_n_mag > 0.01:
                # 法向力系数 ~ CN_alpha * alpha, 简化为正比于侧滑速度
                CN = 2 * v_n_mag / speed * 5.0  # 大致估算的法向力系数
                F_normal = -0.5 * rho * v_n_mag * v_normal * ROCKET_AREA * CN
                F_aero_body[1:3] += F_normal

        # 4. 降落伞阻力 (world frame)
        F_chute_world = np.zeros(3)
        if self.drogue_deployed and not self.main_deployed:
            cd_area = CD_DROGUE * DROGUE_AREA
            F_chute_world = -0.5 * rho * vel * np.linalg.norm(vel) * cd_area
        elif self.main_deployed:
            cd_area = CD_MAIN * MAIN_AREA
            F_chute_world = -0.5 * rho * vel * np.linalg.norm(vel) * cd_area

        # 总力 (body)
        F_body = F_thrust_body + F_grav_body + F_aero_body

        # 转到 world 求加速度
        F_world = R_bw @ F_body + F_chute_world
        accel = F_world / m

        # === 力矩 (body frame) ===
        # 1. 气动恢复力矩 (CP 在 CG 后方, 侧滑产生恢复力矩)
        # body frame: x=轴向, y/z=法向
        # CP 位于 -x_body 方向, 距 CG 为 CP_CG_OFFSET
        # 法向力 N = -k * v_normal (与侧滑速度反向, 起稳定作用)
        # 力矩 M = r_cp × N,  r_cp = [-CP_CG_OFFSET, 0, 0]
        # M_y = -N_z * (-CP_CG_OFFSET) = N_z * CP_CG_OFFSET  (但 N_z = -k*v_z → M_y = -k*CP_CG_OFFSET*v_z)
        # M_z = N_y * (-CP_CG_OFFSET) = -N_y * CP_CG_OFFSET (但 N_y = -k*v_y → M_z = k*CP_CG_OFFSET*v_y)
        M_aero = np.zeros(3)
        if speed > 0.1:
            v_y = v_air_body[1]
            v_z = v_air_body[2]
            # CN_alpha = 15 /rad (典型小型火箭法向力系数导数)
            # 恢复力矩 = -CN_alpha * alpha * Q * S * (CP-CG)
            # 简化为 M = -k * v_normal, k = 0.5*rho*v*S*CN_alpha*(CP-CG)/v_axial
            CN_alpha = 15.0
            v_axial = max(abs(v_air_body[0]), 1.0)
            k_restore = 0.5 * rho * speed * ROCKET_AREA * CN_alpha * CP_CG_OFFSET / v_axial
            # 恢复力矩: 让箭体对准气流
            M_aero[1] = -k_restore * v_z  # 俯仰: v_z 侧滑→绕 y_body 转动
            M_aero[2] = k_restore * v_y   # 偏航: v_y 侧滑→绕 z_body 转动

        # 2. 推力偏斜/TVC 力矩 (推力作用点在 -x 方向, 距 CG 为 L_thrust)
        L_thrust = TOTAL_LENGTH / 2
        r_thrust = np.array([-L_thrust, 0, 0]) + self.mass_offset
        M_thrust = np.cross(r_thrust, F_thrust_body)

        # 3. 阻尼力矩
        M_damp = -0.05 * omega * np.linalg.norm(omega)

        M_total = M_aero + M_thrust + M_damp

        # 角加速度 (body frame)
        # I * dω/dt = M - ω × (I * ω)
        I_diag = np.array([I_XX, I_YY, I_ZZ])
        omega_dot = (M_total - np.cross(omega, I_diag * omega)) / I_diag

        # 四元数导数: q_dot = 0.5 * q ⊗ [0, ω]
        q_dot = 0.5 * quat_mul(q, np.array([0, omega[0], omega[1], omega[2]]))

        # 状态导数
        dstate = np.zeros(13)
        dstate[0:3] = vel
        dstate[3:6] = accel
        dstate[6:10] = q_dot
        dstate[10:13] = omega_dot
        return dstate

    def step(self, dt):
        """RK4 积分一步"""
        # 控制输入
        control = (0.0, 0.0)
        if self.control_fn is not None:
            control = self.control_fn(self.t, self.state)

        # 导轨阶段特殊处理: 强制姿态不变, 只沿导轨方向运动
        if self.phase == "RAIL":
            # 取导轨方向 (初始姿态的 +x_body 在 world 中的方向)
            q = quat_normalize(self.state[6:10])
            R_bw = quat_to_rotmat(q)
            rail_dir = R_bw @ np.array([1, 0, 0])  # 沿箭体轴向上

            # 简化动力学: 沿导轨一维运动
            F = self.thrust
            m = self.mass
            a_along = (F - m * G * rail_dir[2]) / m  # 只考虑重力分量
            if a_along < 0 and self.state[3:6].dot(rail_dir) < 0.01:
                a_along = 0  # 推力不足, 留在导轨上

            v_along = self.state[3:6].dot(rail_dir) + a_along * dt
            self.state[0:3] += rail_dir * v_along * dt
            self.state[3:6] = rail_dir * v_along
            # 姿态和角速度保持初始
            self.t += dt

            # 检查脱离导轨
            dist = np.linalg.norm(self.state[0:3])
            if dist >= RAIL_LENGTH:
                self.phase = "BURN" if self.t < self.t_burn else "COAST"
                self.events.append({"t": self.t, "event": "RAIL_EXIT", "v": float(v_along)})
            return

        # 6DOF 自由飞行: 标准 RK4
        s0 = self.state.copy()
        k1 = self.derivatives(self.t, s0, control)
        s1 = s0 + 0.5 * dt * k1
        k2 = self.derivatives(self.t + 0.5*dt, s1, control)
        s2 = s0 + 0.5 * dt * k2
        k3 = self.derivatives(self.t + 0.5*dt, s2, control)
        s3 = s0 + dt * k3
        k4 = self.derivatives(self.t + dt, s3, control)
        self.state = s0 + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
        # 归一化四元数
        self.state[6:10] = quat_normalize(self.state[6:10])
        self.t += dt

        # 阶段切换
        if self.phase == "BURN" and self.t >= self.t_burn:
            self.phase = "COAST"
            self.events.append({"t": self.t, "event": "BURNOUT", "v": float(np.linalg.norm(self.state[3:6]))})

        if self.phase == "COAST" and self.state[5] < 0:
            # 顶点: 触发减速伞
            self.phase = "DESCENT"
            self.drogue_deployed = True
            self.events.append({"t": self.t, "event": "APOGEE", "h": float(self.state[2])})

            # 主伞在 h < 100m 时开 (在下一次循环检测)
        if self.phase == "DESCENT" and self.drogue_deployed and not self.main_deployed:
            if self.state[2] < 100.0:
                self.main_deployed = True
                self.events.append({"t": self.t, "event": "MAIN_DEPLOY", "h": float(self.state[2])})

        # 着陆
        if self.state[2] < 0 and self.phase != "LAND":
            self.state[2] = 0
            self.state[3:6] = [0, 0, 0]
            self.phase = "LAND"
            self.events.append({"t": self.t, "event": "LANDING", "x": float(self.state[0]), "y": float(self.state[1])})


def run_baseline(motor_name="e12", label="baseline"):
    """运行基准仿真 (开环, 无控制)"""
    print(f"\n[仿真] 启动 6DOF 基准仿真 (motor={motor_name})")
    sim = Rocket6DOF(motor_name=motor_name)

    dt = 0.005
    trajectory = []
    max_h = 0
    while sim.phase != "LAND" and sim.t < 120:
        sim.step(dt)
        # 记录 (10Hz 采样)
        if int(sim.t * 100) % 10 == 0:
            trajectory.append({
                "t": round(sim.t, 3),
                "x": round(float(sim.state[0]), 3),
                "y": round(float(sim.state[1]), 3),
                "z": round(float(sim.state[2]), 3),
                "vx": round(float(sim.state[3]), 3),
                "vy": round(float(sim.state[4]), 3),
                "vz": round(float(sim.state[5]), 3),
                "speed": round(float(np.linalg.norm(sim.state[3:6])), 3),
                "mass": round(sim.mass * 1000, 1),
                "thrust": round(sim.thrust, 2),
                "phase": sim.phase,
            })
            max_h = max(max_h, sim.state[2])

    # 着陆后追加最终状态
    trajectory.append({
        "t": round(sim.t, 3),
        "x": round(float(sim.state[0]), 3),
        "y": round(float(sim.state[1]), 3),
        "z": 0.0,
        "vx": 0, "vy": 0, "vz": 0, "speed": 0,
        "mass": round(sim.mass * 1000, 1),
        "thrust": 0,
        "phase": "LAND",
    })

    # 打印关键事件
    print(f"  飞行事件:")
    for e in sim.events:
        print(f"    t={e['t']:.2f}s  {e['event']:12s}  {e}")

    # 输出 JSON
    output = {
        "label": label,
        "motor": motor_name.upper(),
        "max_altitude_m": round(max_h, 1),
        "flight_time_s": round(sim.t, 2),
        "events": sim.events,
        "trajectory": trajectory,
    }

    out_file = os.path.join(OUTPUT_DIR, f"trajectory_{label}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  [输出] {out_file}  ({len(trajectory)} 采样点)")
    return output


if __name__ == "__main__":
    print("=" * 70)
    print("  Ad Astra 6DOF 飞行仿真 (自研 RK4, E12 基准方案)")
    print("=" * 70)
    print(f"  转动惯量: Ixx={I_XX*1e6:.1f} g·m², Iyy=Izz={I_YY*1e6:.1f} g·m²")
    print(f"  静稳定裕度: {STABILITY_CALIBER} caliber ({CP_CG_OFFSET*1000:.0f}mm)")
    print(f"  导轨: {RAIL_LENGTH}m @ {RAIL_INCLINATION}°")

    out = run_baseline("e12", "baseline")

    print(f"\n  === 飞行摘要 ===")
    print(f"  顶点高度: {out['max_altitude_m']:.1f} m")
    print(f"  飞行时间: {out['flight_time_s']:.2f} s")
    print(f"  着陆位置: x={out['events'][-1].get('x',0):.2f}m, y={out['events'][-1].get('y',0):.2f}m")
