#ifndef GNC_OFFLINE_CASES_H
#define GNC_OFFLINE_CASES_H

// These are native-only source-equivalence checks.  They instantiate the
// production classes (pid.cpp/kalman.cpp are included by the surrounding test
// translation unit), not a copied test controller.  Physical mounting and
// plant polarity are intentionally not asserted here.

void test_production_pid_signed_zero_and_step() {
    PIDController pid(PIDController::FLIGHT);
    const float positive = pid.compute(5.0f, 0.05f);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, -0.3f, positive);

    pid.reset();
    const float negative = pid.compute(-5.0f, 0.05f);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 0.3f, negative);

    pid.reset();
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 0.0f, pid.compute(0.0f, 0.05f));
    TEST_ASSERT_TRUE(pid.compute(2.0f, 0.05f) < 0.0f);
    pid.reset();
    TEST_ASSERT_TRUE(pid.compute(-2.0f, 0.05f) > 0.0f);
}

void test_production_pid_output_and_rate_limits() {
    PIDController pid(PIDController::FLIGHT);
    float previous = 0.0f;
    const float currents[] = {45.0f, -45.0f, 45.0f, 0.0f};
    for (float current : currents) {
        const float output = pid.compute(current, 0.05f);
        TEST_ASSERT_TRUE(output <= 4.0001f);
        TEST_ASSERT_TRUE(output >= -4.0001f);
        TEST_ASSERT_TRUE(output - previous <= 0.3001f);
        TEST_ASSERT_TRUE(output - previous >= -0.3001f);
        previous = output;
    }
}

void test_production_kalman_signed_static_and_step() {
    KalmanFilter zero;
    for (int i = 0; i < 4; ++i) {
        TEST_ASSERT_FLOAT_WITHIN(0.000001f, 0.0f, zero.update(0.0f, 0.0f, 0.01f));
    }

    KalmanFilter positive;
    KalmanFilter negative;
    const float positive_value = positive.update(10.0f, 0.0f, 0.01f);
    const float negative_value = negative.update(-10.0f, 0.0f, 0.01f);
    TEST_ASSERT_TRUE(positive_value > 0.0f);
    TEST_ASSERT_TRUE(negative_value < 0.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.000001f, positive_value, -negative_value);
}

static float run_main_dt_case(unsigned long elapsed_us) {
    FakeSensorBus bus;
    resetFlightHarness(bus);
    // A deterministic positive pitch observation exercises the actual main
    // loop's Kalman/PID dt path without a physical sensor or actuator.
    bus.wordBE(0x68, 0x3B, -8192);
    auto_mode = true;
    lastTime = micros() - elapsed_us;
    loop();
    return kfPitch.getAngle();
}

void test_main_dt_invalid_values_fall_back_to_10ms() {
    const float nominal = run_main_dt_case(10000);
    const float zero_delta = run_main_dt_case(0);
    const float long_delta = run_main_dt_case(600000);
    TEST_ASSERT_FLOAT_WITHIN(0.000001f, nominal, zero_delta);
    TEST_ASSERT_FLOAT_WITHIN(0.000001f, nominal, long_delta);
}

#endif
