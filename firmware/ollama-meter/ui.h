// ui.h — rendering for the 466x466 round AMOLED.
// Canvas double-buffered (M5Canvas in PSRAM, whole-frame push — flicker-free,
// pattern borrowed from reference-m5stack-claude-meter).
#pragma once
#include "net.h"

bool M5LcdInit();   // create canvas; false -> caller paints error (PSRAM issue)
void M5LcdSplash();
void M5LcdPane(uint8_t pane, const MeterData &d);
void M5LcdTick(uint8_t pane, const MeterData &d); // comet anim + page refresh
void M5LcdSetPage(uint8_t page);
uint8_t M5LcdGetPage();

// provisioning screens
void M5LcdConfigScreen(const char *apSsid, const char *apIp); // QR + instructions
void M5LcdMessage(const char *line1, const char *line2 = nullptr);
bool M5LcdDumpFramebuffer();   // host QA: send "DUMP" over serial