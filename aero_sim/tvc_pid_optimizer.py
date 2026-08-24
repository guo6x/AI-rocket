"""
Ad Astra 探空火箭 — TVC PID 仿真调参工具
=======================================
使用 2D 刚体动力学模型模拟火箭姿态控制。
目标：在给定的风扰动或初始偏差下，通过 PID 算法控制舵机偏转，使火箭恢复垂直。
输出：PID 推荐参数、阶跃响应曲线。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import sys

# 导入配置
sys.path.insert(0, os.path.dirname(__file__))
from rocket_config import (
    BODY_OUTER_RADIUS, NOSE_LENGTH, BODY_LENGTH,
    MASS_DRY, MOTOR_DRY_MASS, MOTOR_PROPELLANT_MASS,
    MOTOR_AVG_THRUST, TOTAL_LENGTH
)
from stability_analysis import calc_cg

# ── 1. 物理参数提取 ──
cg_pos, total_mass, components = calc_cg()
# 计算绕重心 (CG) 的横向转动惯量 I (简化为各组件质点模型)
I_total = 0
for name, mass, pos in components:
    I_total += mass * (pos - cg_pos)**2
# 加上主体管自身的转动惯量补偿（简化）
I_total += (1/12) * MASS_DRY * (TOTAL_LENGTH)**2

# 力臂：重心到发动机喷管的距离 (发动机在管底)
L_arm = (NOSE_LENGTH + BODY_LENGTH) - cg_pos

print(f"[INFO] CG Position: {cg_pos:.3f} m")
print(f"[INFO] Launch Mass: {total_mass:.3f} kg")
print(f"[INFO] Moment of Inertia: {I_total:.6f} kg*m^2")
print(f"[INFO] Control Arm: {L_arm:.3f} m")

# ── 2. 仿真设置 ──
dt = 0.01          # 10ms (同步飞控 loop 采样率)
sim_time = 3.0     # 3秒仿真
steps = int(sim_time / dt)

# PID 初始尝试值 (基于经验初选)
# 用户可以在此处修改进行手动优化
KP = 1.2
KI = 0.2
KD = 0.4

# 限制参数
MAX_GIMBAL_ANGLE = 10.0  # 舵机最大偏转角 (deg)
SERVO_SPEED_LIMIT = 300.0 # 舵机转速限制 (deg/s)

def run_simulation(kp, ki, kd, initial_angle=5.0):
    """运行姿态控制仿真"""
    time = np.linspace(0, sim_time, steps)
    angle = np.zeros(steps)      # 当前俯仰角 (deg)
    angular_vel = np.zeros(steps)# 角速度 (deg/s)
    gimbal_angle = np.zeros(steps) # 舵机偏转角 (deg)
    
    error_sum = 0
    last_error = 0
    
    curr_angle = initial_angle
    curr_vel = 0
    curr_gimbal = 0
    
    for i in range(steps):
        # 1. PID 控制器
        error = 0 - curr_angle  # 目标是 0 度 (垂直)
        error_sum += error * dt
        # 积分限幅 (防饱和)
        error_sum = np.clip(error_sum, -10, 10)
        
        d_error = (error - last_error) / dt
        last_error = error
        
        # 计算理想舵机角度
        target_gimbal = kp * error + ki * error_sum + kd * d_error
        target_gimbal = np.clip(target_gimbal, -MAX_GIMBAL_ANGLE, MAX_GIMBAL_ANGLE)
        
        # 模拟舵机物理延迟/限速
        gimbal_diff = target_gimbal - curr_gimbal
        max_diff = SERVO_SPEED_LIMIT * dt
        curr_gimbal += np.clip(gimbal_diff, -max_diff, max_diff)
        
        # 2. 动力学模型
        # 力矩 Q = F * sin(delta) * L
        torque = MOTOR_AVG_THRUST * np.sin(np.radians(curr_gimbal)) * L_arm
        
        # 角加速度 alpha = Q / I (弧度制)
        angular_accel = np.degrees(torque / I_total)
        
        # 积分得到速度和角度
        curr_vel += angular_accel * dt
        curr_angle += curr_vel * dt
        
        # 记录数据
        angle[i] = curr_angle
        angular_vel[i] = curr_vel
        gimbal_angle[i] = curr_gimbal
        
    return time, angle, gimbal_angle

# ── 3. 运行并绘图 ──
plt.figure(figsize=(12, 8))

# 测试几组不同的 PID 组合
configs = [
    (1.2, 0.2, 0.4, '推荐配置'),
    (0.5, 0.1, 0.1, '低增益 (响应慢)'),
    (2.5, 0.5, 0.8, '高增益 (易震荡)')
]

for p, i, d, label in configs:
    t, ang, gim = run_simulation(p, i, d)
    plt.subplot(2, 1, 1)
    plt.plot(t, ang, label=f'{label} (P={p}, I={i}, D={d})')
    plt.subplot(2, 1, 2)
    plt.plot(t, gim, label=f'{label}')

plt.subplot(2, 1, 1)
plt.title('火箭姿态响应 (Pitch Angle Step Response)')
plt.ylabel('俯仰角 [deg]')
plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
plt.grid(True, alpha=0.3)
plt.legend()

plt.subplot(2, 1, 2)
plt.title('TVC 舵机动作 (Gimbal Angle)')
plt.ylabel('偏转角 [deg]')
plt.xlabel('时间 [s]')
plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
plt.grid(True, alpha=0.3)

plt.tight_layout()
os.makedirs('results', exist_ok=True)
plt.savefig('results/tvc_pid_optimization.png', dpi=150)
print(f"\n[DONE] 仿真完成。图表已保存至 results/tvc_pid_optimization.png")
print(f"[RECOM] 建议 PID 初始值: Kp={configs[0][0]}, Ki={configs[0][1]}, Kd={configs[0][2]}")

if __name__ == "__main__":
    plt.show()
