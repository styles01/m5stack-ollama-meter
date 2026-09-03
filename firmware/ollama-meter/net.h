// net.h — WiFi + companion fetch + tiny JSON extraction.
#pragma once
#include <cstdint>
#include "config.h"

#define SESSION_WINDOW_S (5UL * 3600UL)   // ollama.com session window ≈5h

struct LoadedModel {
  char name[24];
  float vramMb;
  int unloadInS;      // seconds until auto-unload, -1 unknown
};

struct MeterData {
  bool valid;              // ever fetched successfully
  // cloud
  bool cloudAvail;
  float sessionPct, weeklyPct;       // -1 = unknown
  long  sessionResetEpoch;           // unix epoch of session reset, 0 unknown
  long  weeklyResetEpoch;            // unix epoch of weekly reset, 0 unknown
  int   sessionResetMin;             // minutes until session reset, -1 unknown
  int   weeklyResetMin;              // minutes until weekly reset, -1 unknown
  float sessionElapsedFrac;          // 0..1 elapsed toward session reset (comet)
  char  topModel[24];                // highest-request model name, "" unknown
  int   topModelReq;                 // its request count
  char  cloudSrc[16];
  int   cloudAgeS;
  // local
  bool serverOk;
  char version[12];
  LoadedModel loaded[3];
  int nLoaded;
  int modelsInstalled;
  // activity
  int todayReq, todayGen, todayErr;
  float reqPerMin;
  // device
  int batteryPct;                    // 0-100, -1 unknown
  bool charging;
  // meta
  uint32_t fetchedMs;
  char raw[3072];
  int rawLen;
  int failCount;
};

void wifiConnect();
void netInit();
bool netFetch(MeterData &d);
bool companionResolve(char *outHost, int outLen);  // mDNS auto or NVS override
int lastHttpCode();

// helpers shared with ui
long isoToEpoch(const char *iso);              // "2026-09-07T00:00:00Z" -> epoch; 0 fail
void formatCountdown(int totalSec, char *out, int outLen);
float sessionTimeFrac(const MeterData &d);     // live comet fraction, computed from clock