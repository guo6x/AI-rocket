import math

class InvertedPendulum1D:
    def __init__(self, mass=1.0, length_cg=0.2, length_thrust=0.5, max_thrust=15.0):
        """
        初始化 1D TVC 倒立摆物理模型
        :param mass: 箭体总质量 (kg)
        :param length_cg: 重心距离底部摆动中心的距离 (m) (现降至 0.2m 方便测试台稳定)
        :param length_thrust: 推力矢量侧向分力作用点距离摆动中心的距离 (m)
                              在倒立摆台面上，推力作用点距转轴一般为 L_t。默认0.5m保证控制力矩充足。
        :param max_thrust: 涵道最大推力 (N)
        """
        self.m = mass
        self.L_cg = length_cg
        self.L_t = length_thrust
        self.F_max = max_thrust
        self.g = 9.81
        
        # 沿底部轴的转动惯量 I = 1/3 * m * L^2 (假设长为 2*L_cg 的均质杆)
        self.I = (1.0 / 3.0) * self.m * (self.L_cg * 2.0)**2
        
        # 状态变量: [俯仰角 theta (rad), 俯仰角速度 theta_dot (rad/s)]
        # 约定：竖直向上为 0 度。顺时针为正。
        self.state = [0.0, 0.0]
        self.time = 0.0

    def reset(self, initial_pitch_deg=0.0):
        self.state = [math.radians(initial_pitch_deg), 0.0]
        self.time = 0.0
        return self.state

    def _derivatives(self, state, servo_angle_rad, thrust):
        theta = state[0]
        theta_dot = state[1]
        
        # 1. 重力产生的倾覆力矩 (使角位移进一步增大)
        # tau_gravity = m*g*L_cg*sin(theta)
        tau_gravity = self.m * self.g * self.L_cg * math.sin(theta)
        
        # 2. 推力产生的控制力矩
        # 原公式：tau_thrust = - thrust * self.L_t * math.sin(servo_angle_rad)
        # 如果箭体 Pitch = +10, PID给出 +x 的 servo angle，那么推力应该产生负的力矩将箭体推回 0。
        # 故 tau_thrust 的负号是正确的。但是当物理步进时，我们传给引擎的是 `actual_servo_angle`
        tau_thrust = - thrust * self.L_t * math.sin(servo_angle_rad)
        
        # 3. 简单的空气阻尼/轴承摩擦力矩，防止无阻尼震荡
        damping_coeff = 0.5  # 增加固有阻尼，帮助收敛
        tau_damping = - damping_coeff * theta_dot
        
        # 总力矩
        tau_total = tau_gravity + tau_thrust + tau_damping
        
        # 角加速度
        theta_ddot = tau_total / self.I
        
        return [theta_dot, theta_ddot]

    def step(self, dt, servo_angle_deg, thrust=None):
        """
        使用 4 阶 Runge-Kutta 进行一步数值积分
        :param dt: 积分时间步长 (s)
        :param servo_angle_deg: 舵机偏角 (度)
        :param thrust: 当前推力 (N)，默认采用最大推力
        :return: (pitch_deg, pitch_rate_deg_s)
        """
        if thrust is None:
            thrust = self.F_max
            
        servo_angle_rad = math.radians(servo_angle_deg)
        
        s = self.state
        
        k1 = self._derivatives(s, servo_angle_rad, thrust)
        
        s_k2 = [s[0] + 0.5 * dt * k1[0], s[1] + 0.5 * dt * k1[1]]
        k2 = self._derivatives(s_k2, servo_angle_rad, thrust)
        
        s_k3 = [s[0] + 0.5 * dt * k2[0], s[1] + 0.5 * dt * k2[1]]
        k3 = self._derivatives(s_k3, servo_angle_rad, thrust)
        
        s_k4 = [s[0] + dt * k3[0], s[1] + dt * k3[1]]
        k4 = self._derivatives(s_k4, servo_angle_rad, thrust)
        
        self.state[0] += (dt / 6.0) * (k1[0] + 2*k2[0] + 2*k3[0] + k4[0])
        self.state[1] += (dt / 6.0) * (k1[1] + 2*k2[1] + 2*k3[1] + k4[1])
        self.time += dt
        
        return math.degrees(self.state[0]), math.degrees(self.state[1])

if __name__ == "__main__":
    # 简易测试代码：无反馈自由倒立摆，初始角度1度，应迅速倒下
    engine = InvertedPendulum1D()
    pitch = engine.reset(initial_pitch_deg=1.0)
    print(f"Time: 0.0s, Pitch: {math.degrees(pitch[0]):.4f} deg")
    for _ in range(10):
        p, pr = engine.step(dt=0.1, servo_angle_deg=0.0)
        print(f"Time: {engine.time:.1f}s, Pitch: {p:.4f} deg")
