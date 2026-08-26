/**
 * @file main.cpp
 * @brief Ad Astra - 阶段六 飞行控制固件 (TVC + Recovery) - 模块化重构版
 */

#include <Adafruit_BMP280.h>
#include <Arduino.h>
#include <Servo.h>
#include <Wire.h>

// 包含新模块
#include "algorithms/kalman.h"
#include "algorithms/pid.h"
#include "command_line_buffer.h"
#include "command_processor.h"
#include "flight_fsm.h"

// ========== 硬件串口显式注册 ==========
HardwareSerial Serial2(USART2);

// ========== 传感器 ==========
Adafruit_BMP280 bmp;
const int MPU_ADDR = 0x68;
const int PWR_MGMT_1 = 0x6B;
const int ACCEL_XOUT_H = 0x3B;
const float ACCEL_SCALE = 16384.0;
const float GYRO_SCALE = 131.0;

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

void applyCommandDecision(const CommandDecision& decision) {
  if (!decision.accepted()) return;

  switch (decision.action) {
    case ACTION_ARM:
      fsm.arm(bmp.readAltitude(1013.25), millis());
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
      const bool was_deployed = fsm.isChuteDeployed();
      fsm.deployChute("GROUND_CMD");
      if (!was_deployed && fsm.isChuteDeployed()) {
        servoRecovery.write(0);
        auto_mode = false;
        commandProcessor.disableAutoForSafety();
        neutralizeTvc();
      }
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
                                   fsm.getState() == FS_IDLE);
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

  if (!bmp.begin(0x76)) {
    Serial.println("[SENSOR] BMP280 FAIL");
  } else {
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL, Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16, Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_1);
    Serial.println("[SENSOR] BMP280 OK");
  }

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(PWR_MGMT_1);
  Wire.write(0);
  Wire.endTransmission();
  Serial.println("[SENSOR] MPU6500 OK");

  kfPitch.init();
  kfRoll.init();

  servoPitch.attach(SERVO_PITCH_PIN);
  servoRoll.attach(SERVO_ROLL_PIN);
  servoPitch.write(90);
  servoRoll.write(90);
  Serial.println("[SERVO] Pitch(PA6) + Roll(PA7) attached. Centered at 90.");

  servoRecovery.attach(SERVO_RECOVERY_PIN);
  servoRecovery.write(90);
  Serial.println("[SERVO] Recovery(PB0) attached. Locked at 90.");

  lastTime = micros();
  delay(500);
  Serial.println("\n====== Ad Astra v6 TVC+Recovery ONLINE ======\n");
}

void loop() {
  handleCommandInput(Serial2, Serial2, serial2CommandBuffer);
  handleCommandInput(Serial, Serial, serialCommandBuffer);

  if (commandProcessor.estopLatched()) {
    delay(50);
    return;
  }

  unsigned long now_us = micros();
  float dt = (now_us - lastTime) / 1000000.0f;
  lastTime = now_us;
  if (dt <= 0 || dt > 0.5) dt = 0.01;

  float altitude = bmp.readAltitude(1013.25);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)14);

  int16_t AcX = Wire.read() << 8 | Wire.read();
  int16_t AcY = Wire.read() << 8 | Wire.read();
  int16_t AcZ = Wire.read() << 8 | Wire.read();
  int16_t Tmp = Wire.read() << 8 | Wire.read();
  int16_t GyX = Wire.read() << 8 | Wire.read();
  int16_t GyY = Wire.read() << 8 | Wire.read();
  int16_t GyZ = Wire.read() << 8 | Wire.read();

  float ax = AcX / ACCEL_SCALE;
  float ay = AcY / ACCEL_SCALE;
  float az = AcZ / ACCEL_SCALE;
  float gx = GyX / GYRO_SCALE;
  float gy = GyY / GYRO_SCALE;
  float gz = GyZ / GYRO_SCALE;

  float pitch_raw = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / PI;
  float roll_raw = atan2(ay, az) * 180.0 / PI;

  float pitch_flt = kfPitch.update(pitch_raw, gy, dt);
  float roll_flt = kfRoll.update(roll_raw, gx, dt);
  float yaw = gz;

  bool was_chute_deployed = fsm.isChuteDeployed();
  fsm.update(az, altitude, millis());

  if (!was_chute_deployed && fsm.isChuteDeployed()) {
    servoRecovery.write(0);
    auto_mode = false;
    commandProcessor.disableAutoForSafety();
    neutralizeTvc();
    Serial.println("[RECOV] !!! CHUTE DEPLOYED !!!");
  }

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
      ", \"auto\":" + String(auto_mode ? 1 : 0) +
      ", \"control_state\":\"" + String(CommandProcessor::stateText(commandProcessor.state())) + "\"" +
      ", \"chute\":" + String(fsm.isChuteDeployed() ? 1 : 0) + ", \"fstate\":\"" +
      String(fsm.getStateStr()) + "\", \"batt\":7.4}";

  Serial.print("[FLIGHT] ");
  Serial.println(json);
  Serial2.println(json);

  delay(50);
}
