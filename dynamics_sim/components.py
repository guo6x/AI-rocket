class SensorModel:
    def __init__(self, update_rate_hz=20.0, delay_ms=50.0):
        """
        模拟 MPU6500+卡尔曼滤波的低刷新率与数据滞后
        :param update_rate_hz: 传感器循环频率 (例如 I2C+融合 的频率 20Hz)
        :param delay_ms: 数据滞后的绝对时间 (例如 50ms)
        """
        self.update_period = 1.0 / update_rate_hz
        self.delay_s = delay_ms / 1000.0
        
        self.time_since_last_update = 0.0
        self.history = []  # 存储 (time, value) 的队列
        self.current_reading = 0.0

    def reset(self):
        self.time_since_last_update = 0.0
        self.history = []
        self.current_reading = 0.0

    def update(self, dt, current_time, true_value):
        """
        在每个积分步长调用
        :param dt: 仿真步长积分时间 (s)
        :param current_time: 当前仿真的绝对时间 (s)
        :param true_value: 当前真实的物理值 (例如真实 pitch)
        :return: 经过传感器模型和延迟后的读取值
        """
        # 1. 记录真实历史以供滞后查询
        self.history.append((current_time, true_value))
        
        # 2. 清理过旧的历史数据以防止内存溢出 (保留比延迟大一点的数据)
        while len(self.history) > 0 and self.history[0][0] < current_time - self.delay_s - 0.1:
            self.history.pop(0)

        # 3. 检查是否到了传感器更新的时间点
        self.time_since_last_update += dt
        if self.time_since_last_update >= self.update_period:
            self.time_since_last_update = 0.0
            
            # 从历史中寻找 delay_s 以前的值
            target_time = current_time - self.delay_s
            
            if target_time <= 0:
                self.current_reading = self.history[0][1] if self.history else 0.0
            else:
                # 寻找最接近 target_time 的历史值
                best_val = self.current_reading
                min_diff = float('inf')
                for t, v in self.history:
                    diff = abs(t - target_time)
                    if diff < min_diff:
                        min_diff = diff
                        best_val = v
                self.current_reading = best_val
                
        return self.current_reading


class ServoModel:
    def __init__(self, update_rate_hz=50.0, max_angle_deg=15.0, deadband_deg=0.5, speed_deg_per_s=600.0):
        """
        模拟 SG92R 烂模拟舵机的物理特性
        :param update_rate_hz: PWM 刷新率 (一般模拟舵机为 50Hz)
        :param max_angle_deg: 结构最大偏角限幅 (例如 +-15度)
        :param deadband_deg: 舵机死区 (输入变化小于此值，舵机不转)
        :param speed_deg_per_s: 舵机最大角速度 (例如 0.1s/60度 -> 600度/s)
        """
        self.update_period = 1.0 / update_rate_hz
        self.max_angle = max_angle_deg
        self.deadband = deadband_deg
        self.max_speed = speed_deg_per_s
        
        self.time_since_last_cmd = 0.0
        
        self.current_angle = 0.0  # 物理实际角度
        self.target_angle = 0.0   # 内部目标角度 (经过死区后)
        
    def reset(self):
        self.time_since_last_cmd = 0.0
        self.current_angle = 0.0
        self.target_angle = 0.0

    def command(self, cmd_angle_deg):
        """
        控制器发送PWM指令
        """
        # 截断限幅
        cmd = max(-self.max_angle, min(self.max_angle, cmd_angle_deg))
        
        # 极烂的死区特性
        if abs(cmd - self.target_angle) > self.deadband:
            self.target_angle = cmd
            
    def step(self, dt):
        """
        物理层面的舵机运动步进 (按积分步长平滑运动)
        :return: 当前物理实际角度
        """
        # 虽然 PWM 是 50Hz, 但模拟舵机内部是一个连续随动系统
        # 我们用匀速模型近似其运动
        angle_diff = self.target_angle - self.current_angle
        
        if abs(angle_diff) > 1e-4:
            # 根据角速度限幅计算本步最大可走角度
            max_step = self.max_speed * dt
            
            if abs(angle_diff) <= max_step:
                self.current_angle = self.target_angle
            else:
                self.current_angle += max_step if angle_diff > 0 else -max_step
                
        return self.current_angle

if __name__ == "__main__":
    # 简易测试代码
    sensor = SensorModel()
    servo = ServoModel()
    
    # 测传感器
    print("Testing Sensor lag...")
    sensor.reset()
    for i in range(100):
        t = i * 0.001
        true_val = t * 10.0 # 10度/秒线性增长
        read_val = sensor.update(0.001, t, true_val)
        if i % 20 == 0:
            print(f"t={t:.3f}, True={true_val:.2f}, Read={read_val:.2f}")

    print("\nTesting Servo slew limits...")
    servo.reset()
    servo.command(10.0)
    for i in range(20):
        t = i * 0.010
        ang = servo.step(0.010)
        print(f"t={t:.3f}, Servo_Ang={ang:.2f}")
