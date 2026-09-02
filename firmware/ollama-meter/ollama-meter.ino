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
    // no creds (or reconfigure requested): the portal is the resting state.
    // Blocks forever until the phone saves; save reboots the device.
    provisionRunPortal(0);
    // (only reachable on unexpected portal exit without save)
    ESP.restart();
  }

  M5LcdSplash();
  wifiConnect();
  if (WiFi.status() == WL_CONNECTED) {
    MLOG("wifi joined: %s", WiFi.localIP().toString().c_str());
  } else {
    MLOG("wifi join FAILED (status %d) -> portal", WiFi.status());
    M5LcdMessage("WiFi failed", "Opening setup...");
    delay(1500);
    provisionRunPortal(0);   // blocks forever until re-saved (then reboots)
    ESP.restart();
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