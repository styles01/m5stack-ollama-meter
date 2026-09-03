// ui.cpp — v7.1 locked design + page system.
// Page 1 (meter): rings + wrapped stats (logo 94px, smaller numbers).
// Page 2 (system): WiFi info + battery + companion, reconfigure hint.
// Buttons: A = next page · B = brightness · C(hold at boot) = setup portal.
#include "ui.h"
#include "net.h"
#include "config.h"
#include "provision.h"
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
static uint8_t g_page = 0;            // 0 = meter face, 1 = system
static uint32_t g_pageAt = 0;

static int jit() { return (int)((millis() / 600000UL) % 5) - 2; }

static uint16_t colorForPct(float p) {
  if (p < 0) return C_DIM;
  if (p < 70) return C_GREEN;
  if (p < 90) return C_AMBER;
  return C_RED;
}

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

static void drawComet(float frac) {
  const float rO = R_TIME_O + 2, rI = R_TIME_I - 2;
  const float rm = (rO + rI) / 2.0f;
  float head = 270.0f + 360.0f * frac;
  const float seg[3][2] = {{-26, -16}, {-15, -6}, {-5, 0}};
  const uint16_t col[3] = {C_TAIL1, C_TAIL2, C_NEUTRAL};
  for (int i = 0; i < 3; i++) {
    float a0 = head + seg[i][0], a1 = head + seg[i][1];
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

// word-wrap a string into <=maxLines lines of <=maxChars chars (mono approx)
static int wrapText(const char *in, int maxChars, int maxLines,
                    char out[][28]) {
  int line = 0, col = 0;
  const char *p = in;
  out[0][0] = 0;
  while (*p && line < maxLines) {
    if (*p == ' ' && col == 0) { p++; continue; }        // no leading spaces
    if (col >= maxChars) {                                // hard break
      out[line][col] = 0;
      line++; if (line >= maxLines) break;
      col = 0; out[line][col] = 0;
      continue;
    }
    out[line][col++] = *p++;
    out[line][col] = 0;
  }
  if (col > 0 && line < maxLines) return line + 1;
  return line ? line : 1;
}

// word-wrap text into lines of <=maxChars chars (breaks on spaces when possible)
static int wrapText(const char *in, int maxChars, char out[][24], int maxLines) {
  int line = 0, col = 0;
  const char *p = in;
  out[0][0] = 0;
  while (*p && line < maxLines) {
    if (*p == ' ' && col == 0) { p++; continue; }
    if (col >= maxChars) {
      // back up to last space in this line if any (nice break)
      int sp = -1;
      for (int i = maxChars; i > maxChars / 2; i--) {
        if (out[line][i] == ' ') { sp = i; break; }
      }
      if (sp > 0) { out[line][sp] = 0; p -= (col - sp - 1); }
      else out[line][col] = 0;
      line++;
      if (line >= maxLines) break;
      col = 0; out[line][0] = 0;
      continue;
    }
    out[line][col++] = *p++;
    out[line][col] = 0;
  }
  return (col || line) ? line + 1 : 1;
}

// word-wrap: fill each line up to maxChars; break AFTER '-' ':' ' ' when the
// next char would exceed maxChars (not at the first break char!)
static int wrapAtBreak(const char *in, int maxChars, char out[][12], int maxLines) {
  int line = 0;
  const char *p = in;
  while (*p && line < maxLines) {
    int col = 0;
    while (*p && col < maxChars) {
      out[line][col++] = *p++;
      // a break char ends the line only if more text follows
      if ((*(p-1) == '-' || *(p-1) == ':' || *(p-1) == ' ') && *p) break;
    }
    // don't leave a trailing space at line end
    while (col > 0 && out[line][col-1] == ' ') { col--; p++; }
    out[line][col] = 0;
    line++;
    if (line < maxLines) out[line][0] = 0;
  }
  return line;
}

static void fmtPct(float v, char *out, int n) {
  if (v < 0) { snprintf(out, n, "--"); return; }
  if (v < 10) snprintf(out, n, "%.1f", v);
  else snprintf(out, n, "%.0f", v);
}

bool M5LcdInit() {
  canvasOk = canvas.createSprite(466, 466);
  if (!canvasOk) { M5.Display.fillScreen(TFT_RED); return false; }
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
  M5.Display.display();
}

void M5LcdSetPage(uint8_t page) { g_page = page; g_pageAt = millis(); }
uint8_t M5LcdGetPage() { return g_page; }

// ------------------------------------------------------------ page 1 face --
static void drawPageMeter(const MeterData &d) {
  canvas.fillScreen(C_BG);
  const uint16_t sessCol = colorForPct(d.sessionPct);

  drawRing(R_WEEK_O, R_WEEK_I, d.weeklyPct, C_CYAN);
  drawRing(R_SESS_O, R_SESS_I, d.sessionPct, sessCol);
  float frac = sessionTimeFrac(d);
  canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 0, 360, C_TRACK);
  if (frac > 0.005f) {
    float a1 = 270.0f + 360.0f * frac;
    if (a1 <= 360.0f) canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 270, a1, C_TFILL);
    else { canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 270, 360, C_TFILL);
           canvas.fillArc(CX, CY, R_TIME_O, R_TIME_I, 0, a1 - 360, C_TFILL); }
  }
  drawComet(frac);

  // LEFT column: logo → model name (Font0, wraps ~8 chars at '-'/' ')
  // → requests (pulled up) → battery at BOTTOM-inside, centered.
  canvas.drawBitmap(CX - 72 - LOGO_W / 2, CY - 59 - LOGO_H / 2,
                    ollama_logo_bits, LOGO_W, LOGO_H, C_INK, C_BG);
  char s[48];
  // model name: EXACTLY 2 lines, deterministic split at last break char
  // ('-' ':') that leaves line1 <= 8 chars; line2 = remainder (cap 10)
  {
    char name[28];
    snprintf(name, sizeof(name), "%s", d.topModel[0] ? d.topModel : "no model");
    char l1[12] = "", l2[12] = "";
    int len = strlen(name);
    int cut = -1;
    for (int i = (len > 8 ? 8 : len) - 1; i >= 4; i--) {
      if (name[i] == '-' || name[i] == ':') { cut = i + 1; break; }
    }
    if (cut < 0) cut = (len > 8) ? 8 : len;
    snprintf(l1, sizeof(l1), "%.*s", cut, name);
    snprintf(l2, sizeof(l2), "%.*s", 10, name + cut);
    canvas.setTextDatum(middle_center);
    canvas.setFont(&fonts::Font0);
    canvas.setTextSize(1);
    canvas.setTextColor(C_INK, C_BG);
    canvas.drawString(l1, CX - 72 + jit(), CY + 2 + jit());
    if (l2[0]) canvas.drawString(l2, CX - 72 + jit(), CY + 12 + jit());
  }
  snprintf(s, sizeof(s), "%d", d.todayReq);
  centerText(CX - 72, CY + 38, s, &fonts::FreeMonoBold12pt7b, 1, C_INK);
  centerText(CX - 72, CY + 60, "requests", &fonts::FreeMono9pt7b, 1, C_DIM);
  // battery: BOTTOM-inside of the rings, horizontally centered
  {
    int bp = d.batteryPct;
    uint16_t bcol = bp < 0 ? C_DIM : (bp < 20 ? C_RED : (bp < 50 ? C_AMBER : C_GREEN));
    if (bp < 0) snprintf(s, sizeof(s), "bat ??");
    else snprintf(s, sizeof(s), "%d%%", bp);
    int gw = 40, gh = 14;
    int gx = CX - (gw + 34) / 2;
    int gy = CY + 116;                    // y=349: inside r146 (chord ~74 half-width)
    canvas.drawRect(gx, gy, gw, gh, C_DIM);
    canvas.fillRect(gx + gw, gy + gh/2 - 3, 3, 6, C_DIM);
    int fw = bp > 0 ? (gw - 4) * bp / 100 : 0;
    if (fw > 0) canvas.fillRect(gx + 2, gy + 2, fw, gh - 4, bcol);
    centerText(gx + gw + 34, gy + 7, s, &fonts::FreeMono9pt7b, 1, bcol);
  }

  // RIGHT column: session + weekly — everything LEFT-ALIGNED at rx, hard
  // carriage returns on the reset lines ("resets in" / value), as specified.
  const int rx = CX + 14;
  leftText(rx, CY - 108, "SESSION", &fonts::FreeMono9pt7b, 1, C_DIM);
  if (d.sessionPct < 0) snprintf(s, sizeof(s), "--");
  else if (d.sessionPct < 10) snprintf(s, sizeof(s), "%.1f%%", d.sessionPct);
  else snprintf(s, sizeof(s), "%.0f%%", d.sessionPct);
  leftText(rx, CY - 72, s, &fonts::FreeMonoBold18pt7b, 1, sessCol);
  {
    char val[20] = "--";
    if (d.sessionResetMin >= 0) {
      int h = d.sessionResetMin / 60, m = d.sessionResetMin % 60;
      if (h >= 24) snprintf(val, sizeof(val), "%dd %02dh", h / 24, h % 24);
      else if (h > 0) snprintf(val, sizeof(val), "%dh %02dm", h, m);
      else snprintf(val, sizeof(val), "%dm", m);
    }
    leftText(rx, CY - 44, "resets in", &fonts::FreeMono9pt7b, 1, C_FAINT);   // HARD line 1
    leftText(rx, CY - 28, val, &fonts::FreeMono9pt7b, 1, C_FAINT);           // HARD line 2
  }
  leftText(rx, CY + 4, "WEEKLY", &fonts::FreeMono9pt7b, 1, C_DIM);
  if (d.weeklyPct < 0) snprintf(s, sizeof(s), "--");
  else if (d.weeklyPct < 10) snprintf(s, sizeof(s), "%.1f%%", d.weeklyPct);
  else snprintf(s, sizeof(s), "%.0f%%", d.weeklyPct);
  leftText(rx, CY + 40, s, &fonts::FreeMonoBold18pt7b, 1, C_CYAN);
  {
    char val[20] = "--";
    if (d.weeklyResetMin >= 0) {
      int h = d.weeklyResetMin / 60, m = d.weeklyResetMin % 60;
      if (h >= 24) snprintf(val, sizeof(val), "%dd %02dh", h / 24, h % 24);
      else if (h > 0) snprintf(val, sizeof(val), "%dh %02dm", h, m);
      else snprintf(val, sizeof(val), "%dm", m);
    }
    leftText(rx, CY + 68, "resets in", &fonts::FreeMono9pt7b, 1, C_FAINT);   // HARD line 1
    leftText(rx, CY + 84, val, &fonts::FreeMono9pt7b, 1, C_FAINT);           // HARD line 2
  }

  canvas.pushSprite(0, 0);
  M5.Display.display();
}

// ------------------------------------------------------------ page 2 sys ---
static void drawPageSys(const MeterData &d) {
  canvas.fillScreen(C_BG);
  char s[48];
  centerText(233, 56, "SYSTEM", &fonts::FreeSansBold18pt7b, 1, C_INK);

  // battery: icon + pct
  int bp = d.batteryPct;
  uint16_t bcol = bp < 0 ? C_DIM : bp < 20 ? C_RED : bp < 50 ? C_AMBER : C_GREEN;
  if (bp < 0) snprintf(s, sizeof(s), "bat ??"); else snprintf(s, sizeof(s), "bat %d%%", bp);
  // battery glyph (outline + fill)
  int bx = 150, by = 96, bw = 120, bh = 34;
  canvas.drawRect(bx, by, bw, bh, C_DIM);
  canvas.fillRect(bx + bw, by + bh/2 - 6, 6, 12, C_DIM);   // nub
  int fw = bp > 0 ? (bw - 6) * bp / 100 : 0;
  if (fw > 0) canvas.fillRect(bx + 3, by + 3, fw, bh - 6, bcol);
  centerText(233, 140, s, &fonts::FreeMono9pt7b, 1, bcol);

  // wifi info
  centerText(233, 190, WiFi.status() == WL_CONNECTED ? "WiFi: connected" : "WiFi: offline",
             &fonts::FreeMono12pt7b, 1, WiFi.status() == WL_CONNECTED ? C_GREEN : C_RED);
  if (WiFi.status() == WL_CONNECTED) {
    centerText(233, 220, WiFi.localIP().toString().c_str(), &fonts::FreeMono9pt7b, 1, C_INK);
    snprintf(s, sizeof(s), "%s  %d dBm", provSsid(), WiFi.RSSI());
    centerText(233, 244, s, &fonts::FreeMono9pt7b, 1, C_DIM);
  }

  // companion + versions
  char host[64];
  extern bool companionResolved(char *out, int n);   // resolved host getter
  companionResolved(host, sizeof(host));
  snprintf(s, sizeof(s), "companion: %s", host);
  centerText(233, 280, s, &fonts::FreeMono9pt7b, 1, C_DIM);
  snprintf(s, sizeof(s), "ollama v%s", d.version);
  centerText(233, 306, s, &fonts::FreeMono9pt7b, 1, C_DIM);

  // actions hint (BtnC is the power button — never used by the app)
  centerText(233, 366, "hold BtnA: reconfigure WiFi", &fonts::FreeSans9pt7b, 1, C_FAINT);
  centerText(233, 392, "BtnA: back to meter", &fonts::FreeSans9pt7b, 1, C_FAINT);

  canvas.pushSprite(0, 0);
  M5.Display.display();
}

void M5LcdPane(uint8_t pane, const MeterData &d) {
  (void)pane;
  if (!canvasOk) return;
  if (g_page == 1) drawPageSys(d);
  else drawPageMeter(d);
}

// tick: comet anim on meter page; page dots always
void M5LcdTick(uint8_t pane, const MeterData &d) {
  (void)pane;
  if (!canvasOk || !d.valid) return;
  static float lastFrac = -1;
  float frac = sessionTimeFrac(d);
  if (g_page == 0 && fabsf(frac - lastFrac) > 0.0015f) {
    lastFrac = frac;
    drawPageMeter(d);
  }
}

// --------------------------------------------------- provisioning screens --
void M5LcdConfigScreen(const char *apSsid, const char *apIp) {
  canvas.fillScreen(C_BG);
  char line[64];
  centerText(233, 64, "METER SETUP", &fonts::FreeSansBold18pt7b, 1, C_GREEN);
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
  centerText(233, 388, "(hold BtnA at boot to reopen)", &fonts::FreeSans9pt7b, 1, C_FAINT);
  canvas.pushSprite(0, 0);
  M5.Display.display();
}

void M5LcdMessage(const char *line1, const char *line2) {
  canvas.fillScreen(C_BG);
  centerText(233, 210, line1, &fonts::FreeSansBold12pt7b, 1, C_INK);
  if (line2) centerText(233, 250, line2, &fonts::FreeSans9pt7b, 1, C_DIM);
  canvas.pushSprite(0, 0);
  M5.Display.display();
}

// framebuffer dump on serial command (host QA): "DUMP\n" -> raw RGB565 LE
bool M5LcdDumpFramebuffer() {
  uint16_t *fb = (uint16_t *)canvas.getBuffer();
  if (!fb) return false;
  Serial.write("METER_FB_DUMP\n");
  const int total = 466 * 466;
  const int CHUNK = 4096;                 // bytes per flush
  const uint8_t *p = (const uint8_t *)fb;
  for (int off = 0; off < total * 2; off += CHUNK) {
    int n = (total * 2 - off) < CHUNK ? (total * 2 - off) : CHUNK;
    Serial.write(p + off, n);
    Serial.flush();
  }
  delay(50);
  return true;
}