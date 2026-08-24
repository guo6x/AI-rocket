import math
import numpy as np
from physics_engine import InvertedPendulum1D
from components import SensorModel, ServoModel
from param_sweep import DiscretePID, run_single_simulation

def find_working_pid(L_cg):
    print(f"Searching for working PID at L_cg = {L_cg}m...")
    # 修改 run_single_simulation 以接受 L_cg
    def sim_with_height(p_i_d):
        kp, ki, kd = p_i_d
        m = 1.15
        L_t = 0.5
        engine = InvertedPendulum1D(mass=m, length_cg=L_cg, length_thrust=L_t, max_thrust=25.0)
        
        sim_dt = 0.001
        sim_duration = 5.0
        sensor = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
        servo = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0, deadband_deg=0.5, speed_deg_per_s=600.0)
        pid = DiscretePID(kp, ki, kd, output_limits=(-15.0, 15.0))
        
        engine.reset(initial_pitch_deg=0.5)
        sensor.reset()
        servo.reset()
        
        cost = 0.0
        time = 0.0
        control_dt = 0.01 
        next_control_time = 0.0
        
        while time < sim_duration:
            true_pitch, _ = engine.state
            true_pitch_deg = math.degrees(true_pitch)
            measured_pitch = sensor.update(sim_dt, time, true_pitch_deg)
            if time >= next_control_time:
                cmd_angle = pid.compute(0.0, measured_pitch, time)
                servo.command(cmd_angle)
                next_control_time += control_dt
            actual_servo_angle = servo.step(sim_dt)
            engine.step(sim_dt, actual_servo_angle)
            cost += abs(true_pitch_deg) * sim_dt
            if abs(true_pitch_deg) > 30.0:
                return kp, ki, kd, 1e6
            time += sim_dt
        return kp, ki, kd, cost

    # 更加精细的 P, D 扫描 (通常这种延迟系统 D 项很关键)
    P_range = np.linspace(0.1, 1.5, 20)
    D_range = np.linspace(0.05, 0.5, 20)
    
    best_cost = 1e7
    best_params = None
    
    for p in P_range:
        for d in D_range:
            _, _, _, cost = sim_with_height((p, 0.0, d))
            if cost < best_cost:
                best_cost = cost
                best_params = (p, 0.0, d)
                
    if best_cost < 1e5:
        print(f"FOUND! Best: Kp={best_params[0]:.2f}, Kd={best_params[2]:.2f}, Cost={best_cost:.4f}")
    else:
        print("Still failing at this height.")
    return best_cost

if __name__ == "__main__":
    heights = [0.1, 0.2, 0.4, 0.6, 0.8]
    for h in heights:
        find_working_pid(h)
