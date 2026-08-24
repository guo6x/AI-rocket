import math
import numpy as np
import matplotlib.pyplot as plt
from physics_engine import InvertedPendulum1D
from components import SensorModel, ServoModel
from param_sweep import DiscretePID

def run_sim(L_cg, kp=1.5, kd=0.4, ki=0.0):
    # 根据 L_cg 调整转动惯量 (假设是长度为 2*L_cg 的杆)
    m = 1.15
    L_t = 0.5 # 固定推力力臂 (假设枢轴在底部以上0.5m处，或者推力在底部以下)
    # 重新实例化引擎以应用新的 L_cg
    engine = InvertedPendulum1D(mass=m, length_cg=L_cg, length_thrust=L_t, max_thrust=25.0)
    
    sim_dt = 0.001
    sim_duration = 5.0
    sensor = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
    servo = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0, deadband_deg=0.5, speed_deg_per_s=600.0)
    pid = DiscretePID(kp, ki, kd, output_limits=(-15.0, 15.0))
    
    engine.reset(initial_pitch_deg=1.0) # 1度扰动
    sensor.reset()
    servo.reset()
    
    time = 0.0
    control_dt = 0.01 
    next_control_time = 0.0
    
    log_t = []
    log_pitch = []
    
    success = True
    while time < sim_duration:
        true_pitch, _ = engine.state
        true_pitch_deg = math.degrees(true_pitch)
        measured_pitch = sensor.update(sim_dt, time, true_pitch_deg)
        
        if time >= next_control_time:
            # 修正极性
            cmd_angle = - pid.compute(0.0, measured_pitch, time)
            servo.command(cmd_angle)
            next_control_time += control_dt
            
        actual_servo_angle = servo.step(sim_dt)
        engine.step(sim_dt, actual_servo_angle)
        
        log_t.append(time)
        log_pitch.append(true_pitch_deg)
        
        if abs(true_pitch_deg) > 30.0:
            success = False
            break
        time += sim_dt
        
    return log_t, log_pitch, success

def study_cg():
    cg_heights = [0.05, 0.1, 0.2, 0.4, 0.6]
    plt.figure(figsize=(10, 6))
    
    print(f"{'L_cg (m)':<10} | {'Status':<10}")
    print("-" * 25)
    
    for h in cg_heights:
        t, p, ok = run_sim(h)
        status = "SUCCESS" if ok else "FAILED"
        print(f"{h:<10.2f} | {status:<10}")
        plt.plot(t, p, label=f"L_cg={h}m ({status})")
        
    plt.axhline(0, color='black', alpha=0.3)
    plt.axhline(30, color='red', linestyle='--', alpha=0.3)
    plt.axhline(-30, color='red', linestyle='--', alpha=0.3)
    plt.title("Impact of CG Height on Stability (with 50ms Delay)")
    plt.xlabel("Time (s)")
    plt.ylabel("Pitch Angle (deg)")
    plt.legend()
    plt.grid(True)
    plt.ylim(-35, 35)
    plt.savefig("cg_impact.png")
    print("\nResult saved to cg_impact.png")

if __name__ == "__main__":
    study_cg()
