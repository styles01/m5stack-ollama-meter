// ollama-meter.ino — M5Stack StopWatch (ESP32-S3, 466x466 round AMOLED)
// Ollama usage meter: v7 locked watch face + captive-portal WiFi provisioning
// (M5Stack UserDemo pattern). Creds live in NVS — no reflash to change WiFi.
// Buttons: A = force refresh · B = brightness · C(hold at boot) = config portal.

#include <M5Unified.h>
#include <WiFi.h>
#include "config.h"
#include "provision.h"
#include "net.h"
#include "ui.h"

static MeterData g;
static uint32_t lastPoll = 0;
static uint32_t lastTick = 0;
static uint8_t brightnessIdx = 0;
static const uint8_t kBrightness[4] = {80, 140, 200, 40};

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Display.setRotation(0);
  M5.Display.setBrightness(180);
#if METER_SERIAL_LOG
  Serial.begin(115200);
#endif
  MLOG("boot");

  if (!M5LcdInit()) {
    while (true) delay(1000);   // red screen = PSRAM problem; stay loud
  }

  M5.update();
  bool forceConfig = M5.BtnC.isPressed();

  bool haveCreds = provisionLoad();
  if (!haveCreds || forceConfig) {
    // blocks; reboots the device on successful save
    provisionRunPortal(300000UL);
    provisionLoad();
  }

  M5LcdSplash();
  wifiConnect();
  if (WiFi.status() == WL_CONNECTED) {
    MLOG("wifi joined: %s", WiFi.localIP().toString().c_str());
  } else {
    MLOG("wifi join FAILED (status %d) -> portal", WiFi.status());
    // join failed (bad password / unreachable) — go back to the portal
    M5LcdMessage("WiFi failed", "Opening setup portal...");
    delay(1500);
    provisionRunPortal(300000UL);   // blocks; reboots on save
    provisionLoad();
    M5LcdSplash();
    wifiConnect();
  }
  netInit();
  lastPoll = 0;
}

void loop() {
  M5.update();

  if (M5.BtnA.wasClicked()) lastPoll = 0;                     // force refresh
  if (M5.BtnB.wasClicked()) {                                 // brightness cycle
    brightnessIdx = (brightnessIdx + 1) % 4;
    M5.Display.setBrightness(kBrightness[brightnessIdx]);
  }

  uint32_t now = millis();
  if (now - lastPoll >= POLL_MS) {
    lastPoll = now;
    netFetch(g);
  }

  if (now - lastTick >= 100) {
    lastTick = now;
    M5LcdTick(0, g);
  }

  delay(10);
}