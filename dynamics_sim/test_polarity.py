import math
import numpy as np
from physics_engine import InvertedPendulum1D
from components import SensorModel, ServoModel
from param_sweep import DiscretePID

def test_polarity():
    m = 1.15
    L_cg = 0.5
    L_t = 0.5
    engine = InvertedPendulum1D(mass=m, length_cg=L_cg, length_thrust=L_t, max_thrust=25.0)
    
    sim_dt = 0.001
    sim_duration = 5.0
    sensor = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
    servo = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0, deadband_deg=0.5, speed_deg_per_s=600.0)
    
    # 尝试一个合理的 Kp, Kd
    kp, ki, kd = 2.0, 0.0, 0.5
    pid = DiscretePID(kp, ki, kd, output_limits=(-15.0, 15.0))
    
    engine.reset(initial_pitch_deg=1.0)
    sensor.reset()
    servo.reset()
    
    time = 0.0
    control_dt = 0.01 
    next_control_time = 0.0
    
    print(f"{'Time':<10} | {'Pitch':<10} | {'Servo':<10}")
    
    while time < sim_duration:
        true_pitch, _ = engine.state
        true_pitch_deg = math.degrees(true_pitch)
        measured_pitch = sensor.update(sim_dt, time, true_pitch_deg)
        
        if time >= next_control_time:
            # 翻转极性：cmd = - pid.compute
            cmd_angle = - pid.compute(0.0, measured_pitch, time)
            servo.command(cmd_angle)
            next_control_time += control_dt
            
        actual_servo_angle = servo.step(sim_dt)
        engine.step(sim_dt, actual_servo_angle)
        
        if int(time * 1000) % 500 == 0:
            print(f"{time:<10.2f} | {true_pitch_deg:<10.2f} | {actual_servo_angle:<10.2f}")
            
        if abs(true_pitch_deg) > 45.0:
            print("CRASHED!")
            break
        time += sim_dt

if __name__ == "__main__":
    test_polarity()
