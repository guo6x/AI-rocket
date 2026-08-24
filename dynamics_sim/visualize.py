import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from param_sweep import run_single_simulation

def plot_heatmap():
    df = pd.read_csv("sweep_results.csv")
    
    # 过滤掉发散的无穷大解 (惩罚项导致 cost > 1e5)
    df_valid = df[df['Cost'] < 1e5]
    
    if len(df_valid) == 0:
        print("警告：所有参数组合均发散，系统极度不稳定！")
        return
        
    # 我们找一个固定的 Kd 切片来画 Kp-Ki 热力图
    # 选取最佳的一组参数
    best_row = df_valid.loc[df_valid['Cost'].idxmin()]
    best_kd = best_row['Kd']
    print(f"最佳全区参数: Kp={best_row['Kp']:.2f}, Ki={best_row['Ki']:.2f}, Kd={best_kd:.2f}, Cost={best_row['Cost']:.2f}")
    
    # 选取与 best_kd 最接近的切片
    df_slice = df_valid[abs(df_valid['Kd'] - best_kd) < 0.01].copy()
    
    # 构建透视表 for seaborn heatmap
    pivot = df_slice.pivot(index='Kp', columns='Ki', values='Cost')
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(pivot, cmap="YlGnBu", annot=True, fmt=".1f")
    plt.title(f"Cost Heatmap @ Kd $\\approx$ {best_kd:.2f}")
    plt.xlabel("Ki")
    plt.ylabel("Kp")
    plt.tight_layout()
    plt.savefig("heatmap.png")
    print("热力图已保存为 heatmap.png")

def plot_best_response():
    df = pd.read_csv("sweep_results.csv")
    df_valid = df[df['Cost'] < 1e5]
    if len(df_valid) == 0:
        return
        
    best_row = df_valid.loc[df_valid['Cost'].idxmin()]
    
    kp, ki, kd = best_row['Kp'], best_row['Ki'], best_row['Kd']
    
    # 重新跑一遍前五秒的时间序列并记录
    import math
    from physics_engine import InvertedPendulum1D
    from components import SensorModel, ServoModel
    from param_sweep import DiscretePID
    
    sim_dt = 0.001
    sim_duration = 5.0
    pendulum = InvertedPendulum1D()
    sensor = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
    servo = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0, deadband_deg=0.5, speed_deg_per_s=600.0)
    pid = DiscretePID(kp, ki, kd, output_limits=(-15.0, 15.0))
    
    pendulum.reset(initial_pitch_deg=0.5)
    sensor.reset()
    servo.reset()
    
    time = 0.0
    control_dt = 0.01 
    next_control_time = 0.0
    
    log_t = []
    log_pitch = []
    log_measured = []
    log_servo = []
    
    while time < sim_duration:
        true_pitch, _ = pendulum.state
        true_pitch_deg = math.degrees(true_pitch)
        measured_pitch = sensor.update(sim_dt, time, true_pitch_deg)
        
        if time >= next_control_time:
            cmd_angle = pid.compute(0.0, measured_pitch, time)
            servo.command(cmd_angle)
            next_control_time += control_dt
            
        actual_servo_angle = servo.step(sim_dt)
        pendulum.step(sim_dt, actual_servo_angle)
        
        log_t.append(time)
        log_pitch.append(true_pitch_deg)
        log_measured.append(measured_pitch)
        log_servo.append(actual_servo_angle)
        
        if abs(true_pitch_deg) > 30.0:
            break
            
        time += sim_dt
        
    plt.figure(figsize=(10, 5))
    plt.plot(log_t, log_pitch, label='True Pitch (deg)', color='blue')
    plt.plot(log_t, log_measured, label='Measured Pitch (20Hz, 50ms delay)', color='orange', alpha=0.7)
    plt.plot(log_t, log_servo, label='Servo Angle (deg, 50Hz cmd)', color='red', linestyle='dashed')
    plt.axhline(0, color='black', linewidth=1)
    
    plt.title(f"Best Response: P={kp:.2f}, I={ki:.2f}, D={kd:.2f}")
    plt.xlabel("Time (s)")
    plt.ylabel("Angle (deg)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("best_response.png")
    print("最佳响应曲线已保存为 best_response.png")

if __name__ == "__main__":
    plot_heatmap()
    plot_best_response()
