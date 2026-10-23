/**
 * @file main.cpp
 * @brief Ad Astra - 阶段六 飞行控制固件 (TVC + Recovery) - 模块化重构版
 */

#include <Arduino.h>
#include <Servo.h>
#include <Wire.h>

// 包含新模块
#include "algorithms/kalman.h"
#include "algorithms/pid.h"
#include "command_line_buffer.h"
#include "command_processor.h"
#include "flight_fsm.h"
#include "sensor_validity.h"
#include "wire_sensor_bus.h"

#ifndef AI_ROCKET_GNC_ONLY_BENCH
#define AI_ROCKET_GNC_ONLY_BENCH 0
#endif

// ========== 硬件串口显式注册 ==========
HardwareSerial Serial2(USART2);

// ========== 传感器 ==========
WireSensorBus sensorBus;
SensorValidity sensors;
SensorSample sensorSample;

// ========== TVC 舵机 ==========
Servo servoPitch;
Servo servoRoll;
const int SERVO_PITCH_PIN = PA6;
const int SERVO_ROLL_PIN = PA7;

// ========== 回收舵机 (REC-01) ==========
Servo servoRecovery;
const int SERVO_RECOVERY_PIN = PB0;

// ========== 模块实例 ==========
KalmanFilter kfPitch, kfRoll;
// 飞行用 PID (Profile::FLIGHT): Kp=1.0/Ki=0.1/Kd=0.3 + 增益调度 + 速率限制
// 同步自 aero_sim/control_simulation.py (重扰动下落点漂移 105m→22m)
PIDController pidPitch(PIDController::FLIGHT), pidRoll(PIDController::FLIGHT);
FlightStateMachine fsm;
CommandProcessor commandProcessor;

bool auto_mode = false;

// ========== 时间追踪 ==========
unsigned long lastTime = 0;

// ========== 每个传输接口拥有独立的命令边界 ==========
CommandLineBuffer serialCommandBuffer;
CommandLineBuffer serial2CommandBuffer;

void neutralizeTvc() {
  servoPitch.write(90);
  servoRoll.write(90);
}

void disableUnsafeControl() {
  auto_mode = false;
  commandProcessor.disableAutoForSafety();
  pidPitch.reset();
  pidRoll.reset();
  neutralizeTvc();
}

void sendSensorState(Print& output) {
  output.print("{\"source_mode\":\"PHYSICAL\",\"sensor_valid\":");
  output.print(sensors.controlReady() ? 1 : 0);
  output.print(",\"sensor_fault\":\"");
  output.print(SensorValidity::faultText(sensors.fault()));
  output.print("\",\"sensor_fault_latched\":");
  output.print(sensors.faultLatched() ? 1 : 0);
  output.print(",\"sensor_io_budget_expired\":");
  output.print(sensorBus.sampleBudgetExpired() ? 1 : 0);
  output.print(",\"auto\":");
  output.print(auto_mode ? 1 : 0);
  output.print(",\"control_state\":\"");
  output.print(CommandProcessor::stateText(commandProcessor.state()));
  output.print("\"");
  output.print(",\"imu_address\":");
  output.print(sensors.imuAddress());
  output.print(",\"imu_id\":");
  output.print(sensors.imuIdentity());
  output.print(",\"bmp_address\":");
  output.print(sensors.bmpAddress());
  output.print(",\"bmp_id\":");
  output.print(sensors.bmpIdentity());
  output.print(",\"time\":");
  output.print(millis());
  // Invalid attitude/altitude are deliberately omitted, not reported as zero.
  output.println("}");
}

void applyCommandDecision(const CommandDecision& decision) {
  if (!decision.accepted()) return;

  switch (decision.action) {
    case ACTION_ARM:
#if !AI_ROCKET_GNC_ONLY_BENCH
      fsm.arm(sensorSample.altitude_m, millis());
#endif
      break;
    case ACTION_AUTO_ON:
      auto_mode = true;
      pidPitch.reset();
      pidRoll.reset();
      break;
    case ACTION_AUTO_OFF:
      auto_mode = false;
      pidPitch.reset();
      pidRoll.reset();
      neutralizeTvc();
      break;
    case ACTION_SET_SERVO:
      servoPitch.write(decision.servo_pitch);
      servoRoll.write(decision.servo_roll);
      break;
    case ACTION_SET_PID:
      pidPitch.setGains(decision.kp, decision.ki, decision.kd);
      pidRoll.setGains(decision.kp, decision.ki, decision.kd);
      break;
    case ACTION_ESTOP:
      auto_mode = false;
      pidPitch.reset();
      pidRoll.reset();
      neutralizeTvc();
      break;
    case ACTION_RESET:
      auto_mode = false;
      pidPitch.reset();
      pidRoll.reset();
      neutralizeTvc();
      fsm.disarm();
      break;
    case ACTION_DEPLOY_CHUTE: {
#if !AI_ROCKET_GNC_ONLY_BENCH
      const bool was_deployed = fsm.isChuteDeployed();
      fsm.deployChute("GROUND_CMD");
      if (!was_deployed && fsm.isChuteDeployed()) {
        servoRecovery.write(0);
        auto_mode = false;
        commandProcessor.disableAutoForSafety();
        neutralizeTvc();
      }
#endif
      break;
    }
    case ACTION_PROFILE_FLIGHT:
      pidPitch.setProfile(PIDController::FLIGHT);
      pidRoll.setProfile(PIDController::FLIGHT);
      break;
    case ACTION_PROFILE_TESTBENCH:
      pidPitch.setProfile(PIDController::TESTBENCH);
      pidRoll.setProfile(PIDController::TESTBENCH);
      break;
    case ACTION_NONE:
      break;
  }
}

void sendCommandResponse(Print& output, const CommandDecision& decision) {
  if (decision.accepted()) {
    output.print("ACK ");
    output.println(decision.command_name);
  } else {
    output.print("NACK ");
    output.print(CommandProcessor::resultText(decision.result));
    output.print(" ");
    output.println(decision.command_name);
  }
}

void handleCommandInput(Stream& input, Print& response,
                        CommandLineBuffer& buffer) {
  while (input.available()) {
    const CommandLineEvent event = buffer.push(static_cast<char>(input.read()));
    if (event == COMMAND_LINE_OVERLONG) {
      response.println("NACK overlong unknown");
    } else if (event == COMMAND_LINE_MALFORMED) {
      response.println("NACK malformed unknown");
    } else if (event == COMMAND_LINE_READY) {
      const CommandDecision decision =
          commandProcessor.process(buffer.line(), fsm.isChuteDeployed(),
                                   fsm.getState() == FS_IDLE,
                                   sensors.controlReady());
      applyCommandDecision(decision);
      sendCommandResponse(response, decision);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200);

  Serial.println("\n\n--- Ad Astra v5: Kalman + Servo + Command Link (Refactored) ---");

  Wire.begin();
  Wire.setClock(100000);

  sensors.begin(sensorBus);
  Serial.print("[SENSOR] ");
  Serial.println(SensorValidity::faultText(sensors.fault()));
  sendSensorState(Serial);

  kfPitch.init();
  kfRoll.init();

  servoPitch.attach(SERVO_PITCH_PIN);
  servoRoll.attach(SERVO_ROLL_PIN);
  servoPitch.write(90);
  servoRoll.write(90);
  Serial.println("[SERVO] Pitch(PA6) + Roll(PA7) attached. Centered at 90.");

#if !AI_ROCKET_GNC_ONLY_BENCH
    servoRecovery.attach(SERVO_RECOVERY_PIN);
    servoRecovery.write(90);
    Serial.println("[SERVO] Recovery(PB0) attached. Locked at 90.");
#else
    Serial.println("[SERVO] Recovery output disabled (GNC-only bench profile).");
#endif

  lastTime = micros();
  delay(500);
  Serial.println("\n====== Ad Astra v6 TVC+Recovery ONLINE ======\n");
}

void loop() {
  // Refresh validity BEFORE either command transport can request ARM/AUTO or
  // manual motion. A previous good sample cannot authorize a failed new cycle.
  sensorBus.beginSample();
  if (!sensors.read(sensorBus, millis(), sensorSample)) disableUnsafeControl();

  handleCommandInput(Serial2, Serial2, serial2CommandBuffer);
  handleCommandInput(Serial, Serial, serialCommandBuffer);

  if (!sensors.controlReady()) {
    sendSensorState(Serial);
    sendSensorState(Serial2);
    delay(50);
    return; // no invalid values enter Kalman, PID, or recovery FSM
  }

  if (commandProcessor.estopLatched()) {
    delay(50);
    return;
  }

  unsigned long now_us = micros();
  float dt = (now_us - lastTime) / 1000000.0f;
  lastTime = now_us;
  if (dt <= 0 || dt > 0.5) dt = 0.01;

  const float altitude = sensorSample.altitude_m;
  const float ax = sensorSample.ax, ay = sensorSample.ay, az = sensorSample.az;
  const float gx = sensorSample.gx, gy = sensorSample.gy, gz = sensorSample.gz;

  float pitch_raw = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / PI;
  float roll_raw = atan2(ay, az) * 180.0 / PI;

  float pitch_flt = kfPitch.update(pitch_raw, gy, dt);
  float roll_flt = kfRoll.update(roll_raw, gx, dt);
  float yaw = gz;

#if !AI_ROCKET_GNC_ONLY_BENCH
    bool was_chute_deployed = fsm.isChuteDeployed();
    fsm.update(az, altitude, millis());

    if (!was_chute_deployed && fsm.isChuteDeployed()) {
      servoRecovery.write(0);
      auto_mode = false;
      commandProcessor.disableAutoForSafety();
      neutralizeTvc();
      Serial.println("[RECOV] !!! CHUTE DEPLOYED !!!");
    }
#endif

  if (auto_mode && !fsm.isChuteDeployed()) {
    int servo_p = constrain(90 + (int)pidPitch.compute(pitch_flt, dt), 0, 180);
    servoPitch.write(servo_p);

    int servo_r = constrain(90 + (int)pidRoll.compute(roll_flt, dt), 0, 180);
    servoRoll.write(servo_r);
  }

  String json =
      "{\"time\":" + String(millis()) +
      ", \"pitch_raw\":" + String(pitch_raw, 2) +
      ", \"pitch_flt\":" + String(pitch_flt, 2) +
      ", \"roll_raw\":" + String(roll_raw, 2) +
      ", \"roll_flt\":" + String(roll_flt, 2) + ", \"yaw\":" + String(yaw, 2) +
      ", \"alt\":" + String(altitude, 2) +
      ", \"sensor_valid\":1, \"source_mode\":\"PHYSICAL\"" +
      ", \"sample_time_ms\":" + String(sensorSample.time_ms) +
      ", \"auto\":" + String(auto_mode ? 1 : 0) +
      ", \"control_state\":\"" + String(CommandProcessor::stateText(commandProcessor.state())) + "\"" +
      ", \"chute\":" + String(fsm.isChuteDeployed() ? 1 : 0) + ", \"fstate\":\"" +
      String(fsm.getStateStr()) + "\", \"batt\":7.4}";

  Serial.print("[FLIGHT] ");
  Serial.println(json);
  Serial2.println(json);

  delay(50);
}
