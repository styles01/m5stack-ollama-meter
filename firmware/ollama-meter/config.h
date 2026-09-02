// config.h — build-time config for the Ollama usage meter.
#pragma once
#include <cstdint>

// Serial lifecycle logging (lightweight, non-blocking) for debugging.
#define METER_SERIAL_LOG 1
#if METER_SERIAL_LOG
  #include <Arduino.h>
  #define MLOG(fmt, ...) Serial.printf("[meter] " fmt "\n", ##__VA_ARGS__)
#else
  #define MLOG(...) do {} while (0)
#endif

// WiFi credentials — NOT used at runtime anymore (NVS provisioning via the
// on-watch setup portal). Kept as documented placeholders only.
#define WIFI_SSID ""
#define WIFI_PASS ""

// Companion service (companion.py on the Mac). Placeholder default — real host
// is set per-device via the on-watch setup portal (provision.cpp) and stored
// in NVS. Find your Mac's LAN IP: System Settings -> Wi-Fi -> Details.
#define COMPANION_HOST ""      // must be provided via setup portal
#define COMPANION_PORT 8615
#define SUMMARY_PATH   "/api/summary"

// Polling / UX timing
#define POLL_MS        10000UL   // companion poll interval
#define AUTO_ROTATE_MS 15000UL   // pane auto-rotate (0 = off)
#define WIFI_TIMEOUT_MS 15000UL
#define REBOOT_AFTER_FAILS 20    // ~3.5 min of continuous failure -> reboot

// Pane ids
#define PANE_CLOUD   0
#define PANE_LOCAL   1
#define PANE_ACTIVITY 2