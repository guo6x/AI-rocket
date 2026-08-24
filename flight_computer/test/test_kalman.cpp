#include <unity.h>
#include "../src/algorithms/kalman.h"
#include "../src/algorithms/kalman.cpp" // 直接包含以方便 native 编译，或者在 platformio.ini 中配置

void test_kalman_initial_state() {
    KalmanFilter kf;
    TEST_ASSERT_EQUAL_FLOAT(0.0f, kf.getAngle());
    TEST_ASSERT_EQUAL_FLOAT(0.0f, kf.getBias());
}

void test_kalman_update() {
    KalmanFilter kf;
    kf.init(0.001f, 0.003f, 0.03f);
    
    // 模拟 1 秒钟，角度从 0 变到 10，角速度为 10
    float angle = kf.update(10.0f, 10.0f, 1.0f);
    
    // 经过一次更新，估计值应该向测量值靠近，但不完全相等（由于滤波）
    TEST_ASSERT_TRUE(angle > 0.0f);
    TEST_ASSERT_TRUE(angle < 15.0f); // 应该在合理范围内
}

void test_kalman_convergence() {
    KalmanFilter kf;
    kf.init(0.001f, 0.003f, 0.03f);
    
    // 多次更新，模拟稳定在 45 度
    float angle = 0;
    for(int i = 0; i < 100; i++) {
        angle = kf.update(45.0f, 0.0f, 0.01f);
    }
    
    // 100次迭代后应该非常接近 45 度
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 45.0f, angle);
}

int main(int argc, char **argv) {
    UNITY_BEGIN();
    RUN_TEST(test_kalman_initial_state);
    RUN_TEST(test_kalman_update);
    RUN_TEST(test_kalman_convergence);
    return UNITY_END();
}
