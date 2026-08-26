#include <unity.h>
#include "../src/algorithms/kalman.h"
#include "../src/algorithms/kalman.cpp" // 直接包含以方便 native 编译，或者在 platformio.ini 中配置
#include "../src/flight_fsm.h"
#include "../src/flight_fsm.cpp"

void setUp() {}
void tearDown() {}

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
    for(int i = 0; i < 1000; i++) {
        angle = kf.update(45.0f, 0.0f, 0.01f);
    }

    // 持续稳定测量后应收敛到 45 度附近。
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 45.0f, angle);
}

static void drive_to_powered(FlightStateMachine &fsm, unsigned long start_ms = 1000) {
    fsm.arm(100.0f, start_ms);
    fsm.update(3.0f, 100.0f, start_ms + 10);
    fsm.update(3.0f, 100.0f, start_ms + 20);
    fsm.update(3.0f, 100.0f, start_ms + 30);
}

void test_fsm_requires_three_launch_samples() {
    FlightStateMachine fsm;
    fsm.arm(100.0f, 1000);
    fsm.update(3.0f, 100.0f, 1010);
    fsm.update(3.0f, 100.0f, 1020);
    TEST_ASSERT_EQUAL(FS_ARMED, fsm.getState());
    fsm.update(3.0f, 100.0f, 1030);
    TEST_ASSERT_EQUAL(FS_POWERED, fsm.getState());
    TEST_ASSERT_EQUAL_UINT32(1030, fsm.getLaunchTime());
}

void test_fsm_launch_counter_resets_after_low_sample() {
    FlightStateMachine fsm;
    fsm.arm(0.0f, 0);
    fsm.update(3.0f, 0.0f, 10);
    fsm.update(1.0f, 0.0f, 20);
    fsm.update(3.0f, 0.0f, 30);
    fsm.update(3.0f, 0.0f, 40);
    TEST_ASSERT_EQUAL(FS_ARMED, fsm.getState());
}

void test_fsm_burnout_and_rolling_apogee_window() {
    FlightStateMachine fsm;
    drive_to_powered(fsm);
    fsm.update(1.0f, 0.0f, 1040);  // burnout; also records first coast altitude
    TEST_ASSERT_EQUAL(FS_COAST, fsm.getState());

    const float altitudes[] = {5.0f, 10.0f, 9.0f, 8.0f, 7.0f};
    for (int i = 0; i < 5; i++) {
        fsm.update(1.0f, altitudes[i], 1050 + i * 10);
    }
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());

    fsm.update(1.0f, 6.0f, 1100);
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_DESCENT, fsm.getState());
}

void test_fsm_timer_is_measured_from_detected_launch() {
    FlightStateMachine fsm;
    drive_to_powered(fsm, 2000);
    fsm.update(1.0f, 0.0f, 2030 + 15000);
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());
    fsm.update(1.0f, 0.0f, 2030 + 15001);
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
}

void test_fsm_manual_deploy_and_reset() {
    FlightStateMachine fsm;
    fsm.arm(12.0f, 500);
    fsm.deployChute("TEST");
    TEST_ASSERT_TRUE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_DESCENT, fsm.getState());
    fsm.reset();
    TEST_ASSERT_FALSE(fsm.isChuteDeployed());
    TEST_ASSERT_EQUAL(FS_IDLE, fsm.getState());
}

int main(int argc, char **argv) {
    UNITY_BEGIN();
    RUN_TEST(test_kalman_initial_state);
    RUN_TEST(test_kalman_update);
    RUN_TEST(test_kalman_convergence);
    RUN_TEST(test_fsm_requires_three_launch_samples);
    RUN_TEST(test_fsm_launch_counter_resets_after_low_sample);
    RUN_TEST(test_fsm_burnout_and_rolling_apogee_window);
    RUN_TEST(test_fsm_timer_is_measured_from_detected_launch);
    RUN_TEST(test_fsm_manual_deploy_and_reset);
    return UNITY_END();
}
