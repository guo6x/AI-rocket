/**
 * @file main.cpp
 * @brief Ad Astra - ESP8266 governed UDP/UART relay
 *
 * 1. STM32 UART telemetry remains UDP broadcast.
 * 2. Explicit unicast UDP commands are validated and forwarded to STM32 UART.
 * 3. STM32 ACK/NACK is unicast back to the most recent command client.
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include "relay_router.h"

#if __has_include("wifi_config.h")
#include "wifi_config.h"
#else
#include "wifi_config.example.h"
#endif

// UDP 广播端口 (地面站 Python 程序监听这个端口)
const unsigned int UDP_PORT = 9876;

WiFiUDP udp;
IPAddress broadcastIP;

// 串口行缓冲
String serialBuffer = "";
IPAddress lastCommandIp;
uint16_t lastCommandPort = 0;
bool hasCommandClient = false;

void sendUdpLine(const IPAddress& ip, uint16_t port, const char* line) {
  udp.beginPacket(ip, port);
  udp.write(reinterpret_cast<const uint8_t*>(line), strlen(line));
  udp.endPacket();
}

void handleUdpCommand() {
  const int packetSize = udp.parsePacket();
  if (packetSize <= 0) return;

  const IPAddress remoteIp = udp.remoteIP();
  const uint16_t remotePort = udp.remotePort();
  uint8_t packet[RelayRouter::MAX_COMMAND_BYTES + 1];
  const int readLength = udp.read(packet, sizeof(packet));
  while (udp.available()) udp.read();

  char command[RelayRouter::MAX_COMMAND_BYTES + 1];
  RelayCommandResult result = RELAY_COMMAND_OVERLONG;
  if (packetSize <= static_cast<int>(RelayRouter::MAX_COMMAND_BYTES) &&
      readLength == packetSize) {
    result = RelayRouter::validateCommandDatagram(
        packet, static_cast<size_t>(readLength), command, sizeof(command));
  }

  if (result != RELAY_COMMAND_READY) {
    sendUdpLine(remoteIp, remotePort,
                result == RELAY_COMMAND_OVERLONG
                    ? "NACK overlong unknown"
                    : "NACK malformed unknown");
    return;
  }

  lastCommandIp = remoteIp;
  lastCommandPort = remotePort;
  hasCommandClient = true;
  Serial.println(command);
}

void setup() {
  Serial.begin(115200);
  delay(100);

  if (USE_AP_MODE) {
    // AP 模式：ESP8266 自己当路由器
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    broadcastIP = IPAddress(192, 168, 4, 255);
  } else {
    // Station 模式：连接已有路由器
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 30) {
      delay(500);
      retries++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      // 计算广播地址
      IPAddress localIP = WiFi.localIP();
      IPAddress subnetMask = WiFi.subnetMask();
      broadcastIP =
          IPAddress(localIP[0] | ~subnetMask[0], localIP[1] | ~subnetMask[1],
                    localIP[2] | ~subnetMask[2], localIP[3] | ~subnetMask[3]);
    } else {
      WiFi.mode(WIFI_AP);
      WiFi.softAP(AP_SSID, AP_PASS);
      broadcastIP = IPAddress(192, 168, 4, 255);
    }
  }

  udp.begin(UDP_PORT);
}

void loop() {
  handleUdpCommand();

  // 从串口逐字节读取，遇到换行符就将整行 UDP 广播出去
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      // ACK/NACK 单播回最近命令客户端；遥测保持原广播回程。
      if (serialBuffer.length() > 0) {
        if (RelayRouter::classifyUartLine(serialBuffer.c_str()) ==
                RELAY_UART_COMMAND_RESPONSE &&
            hasCommandClient) {
          sendUdpLine(lastCommandIp, lastCommandPort, serialBuffer.c_str());
        } else {
          sendUdpLine(broadcastIP, UDP_PORT, serialBuffer.c_str());
        }

        // 清空缓冲，准备接收下一行
        serialBuffer = "";
      }
    } else if (c != '\r') {
      // 忽略回车符，其他字符全部吞入缓冲
      serialBuffer += c;

      // 防止内存溢出：单行超过 512 字节强制截断
      if (serialBuffer.length() > 512) {
        serialBuffer = "";
      }
    }
  }

  // 极短延迟，不阻塞串口读
  yield();
}
