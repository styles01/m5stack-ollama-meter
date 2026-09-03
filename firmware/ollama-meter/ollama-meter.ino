// ollama-meter.ino — M5Stack StopWatch (ESP32-S3, 466x466 round AMOLED)
// Ollama usage meter: v7.1 — page system (meter face + system page),
// captive-portal WiFi provisioning, UDP-beacon companion discovery.
// Buttons: A click = page flip · A hold 2s = config portal · B = brightness.
// BtnC is the POWER button (PMIC) — never used by the app.

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

// battery via M5.Power (routes to the M5PM1 PMIC on StopWatch; same
// 3300-4200mV curve as the official UserDemo hal_pmic.cpp)
static int readBatteryPct() {
  int32_t mv = M5.Power.getBatteryVoltage();
  if (mv <= 0 || mv > 5000) return -1;
  int pct = (int)((mv - 3300) * 100 / (4200 - 3300));
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

static bool readCharging() {
  return M5.Power.isCharging() == m5::Power_Class::is_charging_t::is_charging;
}

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Display.setRotation(0);
  M5.Display.setBrightness(180);
  Serial.begin(115200);            // lifecycle logs + host QA (DUMP command)

  if (!M5LcdInit()) {
    while (true) delay(1000);   // red screen = PSRAM problem; stay loud
  }

  M5.update();
  bool forceConfig = M5.BtnA.isPressed();   // hold A during boot = portal
  // (BtnC is the power button — reserved by the PMIC, never read here)

  bool haveCreds = provisionLoad();
  if (!haveCreds || forceConfig) {
    provisionRunPortal(0);      // blocks forever until saved (then reboots)
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
    provisionRunPortal(0);
    ESP.restart();
  }
  netInit();
  g.batteryPct = readBatteryPct();
  lastPoll = 0;
}

void loop() {
  M5.update();

  // buttons: A click = page flip, A hold 2s = setup portal (BtnC = POWER ONLY,
  // never used by the app — holding it cuts power via the PMIC), B = brightness
  if (M5.BtnA.wasClicked()) {
    M5LcdSetPage(M5LcdGetPage() == 0 ? 1 : 0);
    M5LcdPane(0, g);            // immediate page paint
  }
  if (M5.BtnA.pressedFor(2000)) {
    if (M5LcdGetPage() == 1) M5LcdMessage("Opening setup...", ""); 
    provisionClear();
    ESP.restart();              // boots into portal (no creds)
  }
  if (M5.BtnB.wasClicked()) {
    brightnessIdx = (brightnessIdx + 1) % 4;
    M5.Display.setBrightness(kBrightness[brightnessIdx]);
  }

  static uint32_t lastBat = 0;
  uint32_t now = millis();
  if (now - lastPoll >= POLL_MS) {
    lastPoll = now;
    netFetch(g);
    g.batteryPct = readBatteryPct();
  }
  if (now - lastBat > 60000) {  // battery drifts slowly; 1-min refresh
    lastBat = now;
    g.batteryPct = readBatteryPct();
  }

  if (now - lastTick >= 100) {
    lastTick = now;
    M5LcdTick(0, g);
  }

  // host-side debug: send "DUMP" over serial -> framebuffer dump (non-blocking)
  static char cmdbuf[8] = "";
  static int cmdlen = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      cmdbuf[cmdlen] = 0;
      if (strcmp(cmdbuf, "DUMP") == 0 && M5LcdDumpFramebuffer()) {
        // dump sent
      }
      cmdlen = 0;
    } else if (cmdlen < 7) {
      cmdbuf[cmdlen++] = c;
    }
  }

  delay(10);
}