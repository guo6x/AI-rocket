import math
import multiprocessing
import numpy as np
from physics_engine import InvertedPendulum1D
from components import SensorModel, ServoModel

class DiscretePID:
    def __init__(self, kp, ki, kd, output_limits=(-15.0, 15.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.min_out, self.max_out = output_limits
        
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None
        
    def compute(self, setpoint, measured_value, current_time):
        if self.prev_time is None:
            self.prev_time = current_time
            self.prev_error = setpoint - measured_value
            return 0.0
            
        dt = current_time - self.prev_time
        if dt <= 0:
            return 0.0
            
        error = setpoint - measured_value
        
        # Proportional
        P = self.kp * error
        
        # Integral
        self.integral += error * dt
        I = self.ki * self.integral
        
        # Derivative (on error to handle setpoint kicks, although setpoint is constant here)
        derivative = (error - self.prev_error) / dt
        D = self.kd * derivative
        
        output = P + I + D
        
        # Anti-windup clamping
        if output > self.max_out:
            output = self.max_out
            self.integral -= error * dt # Undo integration if saturated
        elif output < self.min_out:
            output = self.min_out
            self.integral -= error * dt # Undo integration if saturated
            
        self.prev_error = error
        self.prev_time = current_time
        return output

def run_single_simulation(params):
    """
    运行单次带有给定的 P, I, D 参数的仿真
    :param params: (kp, ki, kd)
    :return: (kp, ki, kd, cost)
    """
    kp, ki, kd = params
    
    # 实例化环境
    sim_dt = 0.001
    sim_duration = 5.0 # 仿真 5 秒
    
    pendulum = InvertedPendulum1D()
    # 恢复 20Hz 传感器和 50ms 的滞后
    sensor = SensorModel(update_rate_hz=20.0, delay_ms=50.0) 
    # 恢复烂舵机特性
    servo = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0, deadband_deg=0.5, speed_deg_per_s=600.0)
    pid = DiscretePID(kp, ki, kd, output_limits=(-15.0, 15.0))
    
    # 初始状态：让火箭有 0.5 度的初始倾角扰动
    pendulum.reset(initial_pitch_deg=0.5)
    sensor.reset()
    servo.reset()
    
    cost = 0.0
    time = 0.0
    
    # 控制循环周期 (100Hz 对应 PID 的计算频率，虽然传感器只有 20Hz 更新)
    control_dt = 0.01 
    next_control_time = 0.0
    
    while time < sim_duration:
        # 1. 拿真实的火箭姿态给传感器
        true_pitch, _ = pendulum.state
        true_pitch_deg = math.degrees(true_pitch)
        
        measured_pitch = sensor.update(sim_dt, time, true_pitch_deg)
        
        # 2. 控制器计算
        if time >= next_control_time:
            # 目标永远是 0 度
            cmd_angle = pid.compute(0.0, measured_pitch, time)
            servo.command(cmd_angle)
            next_control_time += control_dt
            
        # 3. 舵机步进
        actual_servo_angle = servo.step(sim_dt)
        
        # 4. 物理引擎步进
        # 注意：此处要考虑控制方向极性。当火箭向正向偏倒时，喷管应该向正向摆动产生反向推力力矩
        # 所以 PID 出来的正方向应使得伺服向正方向偏摆
        pendulum.step(sim_dt, actual_servo_angle)
        
        # 5. 计算 Cost (IAE 积分绝对误差)
        cost += abs(true_pitch_deg) * sim_dt
        
        # \n惩罚机制：如果倒转超过 45 度，视为彻底发散坠毁，提前结束并给罚分
        if abs(true_pitch_deg) > 45.0:
            cost += 1e6
            break
            
        time += sim_dt
        
    return (kp, ki, kd, cost)

def grid_search():
    print("开始控制参数网格扫描 (Grid Search)...")
    
    # 扩大范围：为了烂舵机和长延迟，往往需要较小的 P 以防震荡，以及一定的 D。
    # 也可能是原范围太小没找到。
    P_range = np.linspace(0.01, 2.0, 15)
    I_range = np.linspace(0.0, 0.5, 5)
    D_range = np.linspace(0.01, 1.0, 15)
    
    tasks = []
    for p in P_range:
        for i in I_range:
            for d in D_range:
                tasks.append((p, i, d))
                
    total_tasks = len(tasks)
    print(f"总计参数组合数: {total_tasks}")
    
    # 为了保护 Windows 机器，我们少开几个进程
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
    results = pool.map(run_single_simulation, tasks)
    
    pool.close()
    pool.join()
    
    # 按代价升序排序
    results.sort(key=lambda x: x[3])
    
    print("\n--- 最佳参数 TOP 10 ---")
    for i in range(min(10, len(results))):
        kp, ki, kd, cost = results[i]
        print(f"Rank {i+1}: Kp={kp:.2f}, Ki={ki:.2f}, Kd={kd:.2f} | Cost={cost:.4f}")
        
    # 保存结果到 CSV 供其他工具分析
    with open("sweep_results.csv", "w") as f:
        f.write("Kp,Ki,Kd,Cost\n")
        for r in results:
            f.write(f"{r[0]:.4f},{r[1]:.4f},{r[2]:.4f},{r[3]:.4f}\n")
    print("网格扫描完毕，结果已保存至 sweep_results.csv")

if __name__ == '__main__':
    grid_search()
