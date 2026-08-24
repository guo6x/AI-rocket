/**
 * @file main.cpp
 * @brief Ad Astra - ESP8266 无脑 UDP 透传中继器
 *
 * 功能极其单一且精确：
 * 1. 从串口 RX 接收 STM32 吐出的 JSON 行
 * 2. 通过 WiFi UDP 广播到局域网
 * 3. 不解析，不修改，不缓存。纯透传，极致低延迟。
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

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

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n\n=== Ad Astra: ESP8266 UDP Relay Boot ===");

  if (USE_AP_MODE) {
    // AP 模式：ESP8266 自己当路由器
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    broadcastIP = IPAddress(192, 168, 4, 255);
    Serial.print("AP Mode: SSID=");
    Serial.println(AP_SSID);
    Serial.print("AP IP: ");
    Serial.println(WiFi.softAPIP());
  } else {
    // Station 模式：连接已有路由器
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting to WiFi");

    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 30) {
      delay(500);
      Serial.print(".");
      retries++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println(" OK!");
      Serial.print("IP: ");
      Serial.println(WiFi.localIP());
      // 计算广播地址
      IPAddress localIP = WiFi.localIP();
      IPAddress subnetMask = WiFi.subnetMask();
      broadcastIP =
          IPAddress(localIP[0] | ~subnetMask[0], localIP[1] | ~subnetMask[1],
                    localIP[2] | ~subnetMask[2], localIP[3] | ~subnetMask[3]);
    } else {
      Serial.println(" FAILED! Falling back to AP mode.");
      WiFi.mode(WIFI_AP);
      WiFi.softAP(AP_SSID, AP_PASS);
      broadcastIP = IPAddress(192, 168, 4, 255);
    }
  }

  udp.begin(UDP_PORT);
  Serial.print("UDP relay active on port ");
  Serial.println(UDP_PORT);
  Serial.println("=== RELAY ONLINE. Waiting for STM32 data... ===\n");
}

void loop() {
  // 从串口逐字节读取，遇到换行符就将整行 UDP 广播出去
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      // 一行完整的 JSON 已到手，立刻发射！
      if (serialBuffer.length() > 0) {
        udp.beginPacket(broadcastIP, UDP_PORT);
        udp.write((const uint8_t *)serialBuffer.c_str(), serialBuffer.length());
        udp.endPacket();

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
