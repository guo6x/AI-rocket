import math
import matplotlib.pyplot as plt
from physics_engine import InvertedPendulum1D
from components import SensorModel, ServoModel
from param_sweep import DiscretePID

def debug_divergence():
    print("----- 开始无发散强制终止的单次详细推演 -----")
    # 使用上一轮扫描中看似较好的数据 (Cost 最低的一组)
    kp = 0.58
    ki = 0.0
    kd = 0.15
    
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
    log_cmd = []
    log_servo = []
    
    while time < sim_duration:
        true_pitch, _ = pendulum.state
        true_pitch_deg = math.degrees(true_pitch)
        measured_pitch = sensor.update(sim_dt, time, true_pitch_deg)
        
        cmd_angle = pid.prev_error # just placeholder scoping
        if time >= next_control_time:
            cmd_angle = pid.compute(0.0, measured_pitch, time)
            servo.command(cmd_angle)
            next_control_time += control_dt
            
        actual_servo_angle = servo.step(sim_dt)
        pendulum.step(sim_dt, actual_servo_angle)
        
        log_t.append(time)
        log_pitch.append(true_pitch_deg)
        log_measured.append(measured_pitch)
        log_cmd.append(servo.target_angle)
        log_servo.append(actual_servo_angle)
        
        time += sim_dt
        
    plt.figure(figsize=(12, 6))
    plt.plot(log_t, log_pitch, label='True Pitch (deg)')
    plt.plot(log_t, log_measured, label='Measured Pitch (20ms delay)')
    plt.plot(log_t, log_cmd, label='PID Command Angle')
    plt.plot(log_t, log_servo, label='Actual Servo Angle')
    
    plt.axhline(0, color='black')
    plt.title("Divergence Debug: Kp=1.0, Ki=0.1, Kd=0.5")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("debug_divergence.png")
    print("绘制完成: debug_divergence.png")
    
if __name__ == "__main__":
    debug_divergence()
