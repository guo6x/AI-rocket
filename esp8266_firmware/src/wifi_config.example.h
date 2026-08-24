#pragma once

// Copy this file to wifi_config.h and replace the placeholder values.
// wifi_config.h is ignored by Git so local credentials are not published.
constexpr char WIFI_SSID[] = "YOUR_WIFI_SSID";
constexpr char WIFI_PASS[] = "YOUR_WIFI_PASSWORD";

// Set to true to let the ESP8266 create its own access point.
constexpr bool USE_AP_MODE = false;
constexpr char AP_SSID[] = "AdAstra_Rocket";
constexpr char AP_PASS[] = "CHANGE_ME_12345678";

