#ifndef KALMAN_1D_H
#define KALMAN_1D_H

/**
 * @brief 极其简单的单维度(Z轴高度与垂直速度)卡尔曼滤波器
 *
 * 用于将带噪音的气压计高度测量值与相对平滑但会漂移的Z轴加速度值(积分)结合，
 * 输出高频且平滑的当前绝对高度与垂直速度。
 */
class Kalman1D {
private:
  // 状态向量: [高度(z), 垂直速度(v)]T
  float z;
  float v;

  // 协方差矩阵 P: 表示对当前状态估计的"不确定度"
  float P_zz, P_zv, P_vz, P_vv;

  // 过程噪声方差 Q: 系统模型自身的不准确度 (主要由加速度噪音引起)
  float Q_accel;

  // 测量噪声方差 R: 传感器的不准确度 (气压计高度读数的噪音)
  float R_altitude;

public:
  Kalman1D(float init_z_variance, float init_v_variance, float accel_variance,
           float sensor_variance) {
    z = 0.0f;
    v = 0.0f;

    P_zz = init_z_variance;
    P_zv = 0.0f;
    P_vz = 0.0f;
    P_vv = init_v_variance;

    Q_accel = accel_variance;
    R_altitude = sensor_variance;
  }

  /**
   * @brief 第一步: 预测 (Predict)
   * 根据物理运动学公式预测下一时刻的状态: S_t = S_t-1 + V * dt + 0.5 * A * dt^2
   *
   * @param accel_z 减去1G重力后的当前垂直向上的实际加速度 (m/s^2)
   * @param dt 距离上一次计算过去的时间间隔 (秒)
   */
  void predict(float accel_z, float dt) {
    // 1. 预测状态
    z += v * dt + 0.5f * accel_z * dt * dt;
    v += accel_z * dt;

    // 2. 预测误差协方差
    // 矩阵运算展开: P = F*P*F^T + Q
    float P_zz_temp = P_zz + dt * P_vz + dt * (P_zv + dt * P_vv);
    float P_zv_temp = P_zv + dt * P_vv;
    float P_vz_temp = P_vz + dt * P_vv;
    float P_vv_temp = P_vv;

    P_zz = P_zz_temp + 0.25f * Q_accel * dt * dt * dt * dt;
    P_zv = P_zv_temp + 0.5f * Q_accel * dt * dt * dt;
    P_vz = P_vz_temp + 0.5f * Q_accel * dt * dt * dt;
    P_vv = P_vv_temp + Q_accel * dt * dt;
  }

  /**
   * @brief 第二步: 更新/校正 (Update)
   * 用气压计实际测量到的高度，去修正刚才"预测"得到的状态。
   *
   * @param measured_z 气压计解算出的高度 (米)
   */
  void update(float measured_z) {
    // 1. 计算创新(Innovation) / 测量残差 (y = Z - H*x)
    float y = measured_z - z;

    // 2. 计算创新协方差 (S = H*P*H^T + R)
    float S = P_zz + R_altitude;

    // 3. 计算卡尔曼增益 (K = P*H^T * S^-1)
    float K_z = P_zz / S;
    float K_v = P_vz / S;

    // 4. 更新状态估计 (x = x + K*y)
    z += K_z * y;
    v += K_v * y;

    // 5. 更新误差协方差 (P = (I - K*H)*P)
    float P_zz_new = (1.0f - K_z) * P_zz;
    float P_zv_new = (1.0f - K_z) * P_zv;
    float P_vz_new = -K_v * P_zz + P_vz;
    float P_vv_new = -K_v * P_zv + P_vv;

    P_zz = P_zz_new;
    P_zv = P_zv_new;
    P_vz = P_vz_new;
    P_vv = P_vv_new;
  }

  float getAltitude() const { return z; }
  float getVelocity() const { return v; }
};

#endif // KALMAN_1D_H
