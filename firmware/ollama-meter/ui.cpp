// ui.cpp — v7 LOCKED DESIGN (design/DESIGN-LOCKED.md)
// Watch face: weekly ring (ALWAYS cyan, outer), session ring (threshold color),
// neutral reset-timer ring with comet head = session-window time elapsed.
// ALL text inside r<=146 of center. Big % numbers color-matched to their rings.
// Canvas double-buffered in PSRAM (pattern from reference-m5stack-claude-meter).
#include "ui.h"
#include "net.h"
#include "config.h"
#include "ollama_logo.h"
#include <M5Unified.h>
#include <WiFi.h>
#include <cstring>
#include <cstdio>
#include <cmath>

// ---------------- palette — computed from DESIGN-LOCKED.md RGB values ------
static inline uint16_t RGB565(int r, int g, int b) {
  return (uint16_t)(((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3));
}
static const uint16_t C_BG     = RGB565(9,11,17);
static const uint16_t C_INK    = RGB565(240,242,248);
static const uint16_t C_DIM    = RGB565(122,130,150);
static const uint16_t C_FAINT  = RGB565(84,92,114);
static const uint16_t C_TRACK  = RGB565(30,34,48);
static const uint16_t C_CYAN   = RGB565(86,208,226);   // WEEKLY ONLY
static const uint16_t C_GREEN  = RGB565(52,199,120);
static const uint16_t C_AMBER  = RGB565(255,184,66);
static const uint16_t C_RED    = RGB565(255,92,92);
static const uint16_t C_NEUTRAL= RGB565(200,206,222);  // timer ring only
static const uint16_t C_TAIL1  = RGB565(60,66,88);
static const uint16_t C_TAIL2  = C_DIM;
static const uint16_t C_TFILL  = RGB565(96,104,124);   // timer ring elapsed fill

// geometry (DESIGN-LOCKED.md)
static const int CX = 233, CY = 233;
static const int R_WEEK_O = 200, R_WEEK_I = 188;
static const int R_SESS_O = 180, R_SESS_I = 168;
static const int R_TIME_O = 158, R_TIME_I = 152;
static const float DEG_TO_RAD_F = 0.0174532925f;

static M5Canvas canvas(&M5.Display);
static bool canvasOk = false;

// AMOLED burn-in mitigation (reference repo): text drifts +-2px on 10-min cycle
static int jit() { return (int)((millis() / 600000UL) % 5) - 2; }

static uint16_t colorForPct(float p) {
  if (p < 0) return C_DIM;
  if (p < 70) return C_GREEN;
  if (p < 90) return C_AMBER;
  return C_RED;
}

// ring: full track + pct sweep from 12 o'clock (270deg LGFX), rounded caps
static void drawRing(int rO, int rI, float pct, uint16_t color) {
  canvas.fillArc(CX, CY, rO, rI, 0, 360, C_TRACK);
  if (pct < 0 || pct <= 0.2f) return;
  if (pct > 100) pct = 100;
  float sweep = 360.0f * pct / 100.0f;
  float a0 = 270.0f, a1 = a0 + sweep;
  if (a1 <= 360.0f) canvas.fillArc(CX, CY, rO, rI, a0, a1, color);
  else {
    canvas.fillArc(CX, CY, rO, rI, a0, 360, color);
    canvas.fillArc(CX, CY, rO, rI, 0, a1 - 360.0f, color);
  }
  float rm = (rO + rI) / 2.0f, rc = (rO - rI) / 2.0f;
  float aa[2] = {a0, a1};
  for (int i = 0; i < 2; i++) {
    float rad = aa[i] * DEG_TO_RAD_F;
    canvas.fillCircle(CX + (int)(cosf(rad) * rm), CY + (int)(sinf(rad) * rm), (int)rc, color);
  }
}

// comet head on the timer ring: 3 fading segments ending at `frac` of the window
static void drawComet(float frac) {
  const float rO = R_TIME_O + 2, rI = R_TIME_I - 2;  // slightly proud of the band
  const float rm = (rO + rI) / 2.0f;
  float head = 270.0f + 360.0f * frac;               // LGFX angle of the head
  const float seg[3][2] = {{-26, -16}, {-15, -6}, {-5, 0}};
  const uint16_t col[3] = {C_TAIL1, C_TAIL2, C_NEUTRAL};
  for (int i = 0; i < 3; i++) {
    float a0 = head + seg[i][0], a1 = head + seg[i][1];
    // wrap-safe fillArc
    if (a0 < 0) a0 += 360;
    if (a1 < 0) a1 += 360;
    if (a0 > a1) {
      canvas.fillArc(CX, CY, (int)rO, (int)rI, a0, 360, col[i]);
      canvas.fillArc(CX, CY, (int)rO, (int)rI, 0, a1, col[i]);
    } else {
      canvas.fillArc(CX, CY, (int)rO, (int)rI, a0, a1, col[i]);
    }
  }
  float rad = head * DEG_TO_RAD_F;
  canvas.fillCircle(CX + (int)(cosf(rad) * rm), CY + (int)(sinf(rad) * rm), 4, C_NEUTRAL);
}

static void centerText(int x, int y, const char *s, const lgfx::v1::IFont *font,
                       uint8_t size, uint16_t color) {
  canvas.setTextDatum(middle_center);
  canvas.setTextSize(size);
  canvas.setFont(font);
  canvas.setTextColor(color, C_BG);
  canvas.drawString(s, x + jit(), y + jit());
}

static void leftText(int x, int y, const char *s, const lgfx::v1::IFont *font,
                     uint8_t size, uint16_t color) {
  canvas.setTextDatum(top_left);
  canvas.setTextSize(size);
  canvas.setFont(font);
  canvas.setTextColor(color, C_BG);
  canvas.drawString(s, x + jit(), y + jit());
}

bool M5LcdInit() {
  canvasOk = canvas.createSprite(466, 466);
  if (!canvasOk) {
    M5.Display.fillScreen(TFT_RED);   // loud failure: PSRAM misconfig
    return false;
  }
  return true;
}

void M5LcdSplash() {
  canvas.fillScreen(C_BG);
  canvas.setTextDatum(middle_center);
  canvas.setFont(&fonts::FreeSansBold24pt7b);
  canvas.setTextSize(2);
  canvas.setTextColor(C_INK, C_BG);
  canvas.drawString("OLLAMA", 233, 170);
  canvas.setTextColor(C_INK, C_BG);
  canvas.drawString("METER", 233, 240);
  canvas.setFont(&fonts::FreeSans9pt7b);
  canvas.setTextSize(1);
  canvas.setTextColor(C_DIM, C_BG);
  canvas.drawString(WiFi.status() == WL_CONNECTED
                        ? WiFi.localIP().toString().c_str()
                        : "joining wifi...",
                    233, 320);
  canvas.pushSprite(0, 0);
  M5.Display.display();   // panel refresh needed on the StopWatch round AMOLED
}

// ------------------------------------------------------------ the face ----
void M5LcdPane(uint8_t pane, const MeterData &d) {
  (void)pane;
  if (!canvasOk) return;
  canvas.fillScreen(C_BG);

  if (!d.valid) {
    centerText(CX, CY, "connecting...", &fonts::FreeSans12pt7b, 1, C_DIM);
    canvas.pushSprite(0, 0);
    return;
  }

  const uint16_t sessCol = colorForPct(d.sessionPct);

  // --- three rings ---
  drawRing(R_WEEK_O, R_WEEK_I, d.weeklyPct, C_CYAN);   // weekly: ALWAYS cyan
  drawRing(R_SESS_O, R_SESS_I, d.sessionPct, sessCol);// session: threshold color
  // timer ring: full neutral track; fill = elapsed (comet adds the head)
  float frac = sessionTimeFrac(d);
  canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 0, 360, C_TRACK);
  if (frac > 0.005f) {
    float a1 = 270.0f + 360.0f * frac;
    if (a1 <= 360.0f) canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 270, a1, C_TFILL);
    else { canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 270, 360, C_TFILL);
           canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 0, a1 - 360, C_TFILL); }
  }
  drawComet(frac);

  // --- inner circle: LEFT column (logo + activity) ---
  canvas.drawBitmap(CX - 72 - LOGO_W / 2, CY - 60 - LOGO_H / 2,
                    ollama_logo_bits, LOGO_W, LOGO_H, C_INK, C_BG);
  char s[40];
  snprintf(s, sizeof(s), "%.1f", d.reqPerMin);
  centerText(CX - 72, CY + 26, s, &fonts::FreeMonoBold12pt7b, 1, C_INK);
  centerText(CX - 72, CY + 52, "req/min", &fonts::FreeMono9pt7b, 1, C_DIM);
  snprintf(s, sizeof(s), "%d req %d gen", d.todayReq, d.todayGen);
  centerText(CX - 58, CY + 76, s, &fonts::FreeMono9pt7b, 1, C_FAINT);

  // --- inner circle: RIGHT column (color-matched big numbers) ---
  const int rx = CX + 14;
  leftText(rx, CY - 112, "SESSION", &fonts::FreeMono9pt7b, 1, C_DIM);
  if (d.sessionPct < 0) snprintf(s, sizeof(s), "--");
  else if (d.sessionPct < 10) snprintf(s, sizeof(s), "%.1f%%", d.sessionPct);
  else snprintf(s, sizeof(s), "%.0f%%", d.sessionPct);
  centerText(rx + 60, CY - 76, s, &fonts::FreeMonoBold24pt7b, 1, sessCol);
  if (d.sessionResetMin >= 0) {
    char cd[16]; formatCountdown(d.sessionResetMin * 60, cd, sizeof(cd));
    snprintf(s, sizeof(s), "resets %s", cd);
    leftText(rx, CY - 48, s, &fonts::FreeMono9pt7b, 1, C_FAINT);
  }
  leftText(rx, CY - 16, "WEEKLY", &fonts::FreeMono9pt7b, 1, C_DIM);
  if (d.weeklyPct < 0) snprintf(s, sizeof(s), "--");
  else if (d.weeklyPct < 10) snprintf(s, sizeof(s), "%.1f%%", d.weeklyPct);
  else snprintf(s, sizeof(s), "%.0f%%", d.weeklyPct);
  centerText(rx + 60, CY + 22, s, &fonts::FreeMonoBold24pt7b, 1, C_CYAN);
  if (d.weeklyResetMin >= 0) {
    char cd[16]; formatCountdown(d.weeklyResetMin * 60, cd, sizeof(cd));
    snprintf(s, sizeof(s), "resets %s", cd);
    leftText(rx, CY + 52, s, &fonts::FreeMono9pt7b, 1, C_FAINT);
  }

  canvas.pushSprite(0, 0);
  M5.Display.display();   // panel refresh needed on the StopWatch round AMOLED
}

// tick: live comet interpolation + redraw when the fraction moves
void M5LcdTick(uint8_t pane, const MeterData &d) {
  (void)pane;
  if (!canvasOk || !d.valid) return;
  static float lastFrac = -1;
  float frac = sessionTimeFrac(d);
  if (fabsf(frac - lastFrac) > 0.0015f) {   // ~0.5 deg of arc
    lastFrac = frac;
    M5LcdPane(0, d);
  }
}

// --------------------------------------------------- provisioning screens --
void M5LcdConfigScreen(const char *apSsid, const char *apIp) {
  canvas.fillScreen(C_BG);
  char line[64];
  centerText(233, 64, "METER SETUP", &fonts::FreeSansBold18pt7b, 1, C_GREEN);
  // QR of the portal URL, left side; instructions right
  snprintf(line, sizeof(line), "http://%s", apIp);
  canvas.qrcode(line, 34, 118, 180, 3);
  canvas.setTextDatum(top_left);
  canvas.setFont(&fonts::FreeSans9pt7b);
  canvas.setTextSize(1);
  canvas.setTextColor(C_INK, C_BG);
  canvas.drawString("1. Join WiFi:", 244, 120);
  canvas.setTextColor(C_GREEN, C_BG);
  canvas.drawString(apSsid, 244, 140);
  canvas.setTextColor(C_INK, C_BG);
  canvas.drawString("2. Scan QR or open:", 244, 176);
  canvas.setTextColor(C_GREEN, C_BG);
  canvas.drawString(line, 244, 196);
  canvas.setTextColor(C_DIM, C_BG);
  canvas.drawString("3. Pick network + save", 244, 232);
  centerText(233, 388, "(hold BtnC at boot to reopen)", &fonts::FreeSans9pt7b, 1, C_FAINT);
  canvas.pushSprite(0, 0);
  M5.Display.display();
}

void M5LcdMessage(const char *line1, const char *line2) {
  canvas.fillScreen(C_BG);
  centerText(233, 210, line1, &fonts::FreeSansBold12pt7b, 1, C_INK);
  if (line2) centerText(233, 250, line2, &fonts::FreeSans9pt7b, 1, C_DIM);
  canvas.pushSprite(0, 0);
  M5.Display.display();   // panel refresh needed on the StopWatch round AMOLED
}