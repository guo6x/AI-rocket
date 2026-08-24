#ifndef KALMAN_H
#define KALMAN_H

/**
 * @class KalmanFilter
 * @brief 一维卡尔曼滤波器，用于姿态角度估计（融合陀螺仪角速度和加速度计角度测量）
 */
class KalmanFilter {
public:
    KalmanFilter();

    /**
     * @brief 初始化滤波器参数
     * @param q_angle 过程噪声（角度）
     * @param q_bias 过程噪声（偏差）
     * @param r_measure 测量噪声
     */
    void init(float q_angle = 0.001f, float q_bias = 0.003f, float r_measure = 0.03f);

    /**
     * @brief 更新滤波器状态
     * @param newAngle 新的角度测量值（来自加速度计）
     * @param newRate 新的角速度测量值（来自陀螺仪）
     * @param dt 时间间隔（秒）
     * @return 估计的角度值
     */
    float update(float newAngle, float newRate, float dt);

    float getAngle() const { return angle; }
    float getBias() const { return bias; }

private:
    float angle;   // 估计角度
    float bias;    // 陀螺仪偏差估计
    float P[2][2]; // 误差协方差矩阵

    float Q_angle;   // 过程噪声（角度）
    float Q_bias;    // 过程噪声（偏差）
    float R_measure; // 测量噪声
};

#endif // KALMAN_H
