#include "kalman.h"

KalmanFilter::KalmanFilter() {
    init();
}

void KalmanFilter::init(float q_angle, float q_bias, float r_measure) {
    angle = 0.0f;
    bias = 0.0f;
    Q_angle = q_angle;
    Q_bias = q_bias;
    R_measure = r_measure;
    
    P[0][0] = 0.0f;
    P[0][1] = 0.0f;
    P[1][0] = 0.0f;
    P[1][1] = 0.0f;
}

float KalmanFilter::update(float newAngle, float newRate, float dt) {
    // 预测步 (Predict)
    float rate = newRate - bias;
    angle += dt * rate;

    P[0][0] += dt * (dt * P[1][1] - P[0][1] - P[1][0] + Q_angle);
    P[0][1] -= dt * P[1][1];
    P[1][0] -= dt * P[1][1];
    P[1][1] += Q_bias * dt;

    // 更新步 (Update)
    float S = P[0][0] + R_measure; // 新息协方差
    float K[2];                    // 卡尔曼增益
    K[0] = P[0][0] / S;
    K[1] = P[1][0] / S;

    float y = newAngle - angle; // 新息 (测量残差)
    angle += K[0] * y;
    bias += K[1] * y;

    float P00_temp = P[0][0];
    float P01_temp = P[0][1];
    P[0][0] -= K[0] * P00_temp;
    P[0][1] -= K[0] * P01_temp;
    P[1][0] -= K[1] * P00_temp;
    P[1][1] -= K[1] * P01_temp;

    return angle;
}
