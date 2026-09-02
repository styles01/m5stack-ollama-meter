// net.cpp — WiFi, companion HTTP, tiny JSON extraction, payload diffing.
#include "net.h"
#include "config.h"
#include "provision.h"
#include <ESPmDNS.h>
#include <M5Unified.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <ctime>

// ---------------------------------------------------------------- wifi ----
void wifiConnect() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(provSsid(), provPass());     // creds from NVS (provision.cpp)
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < WIFI_TIMEOUT_MS) {
    delay(120);
  }
}

// ------------------------------------------------------- tiny json tool ----
struct JVal {
  const char *p;
  int len;
  bool isStr;
  bool found;
};

static JVal jfind(const char *from, const char *key) {
  JVal v = {nullptr, 0, false, false};
  char pat[48];
  snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char *k = strstr(from, pat);
  if (!k) return v;
  const char *c = strchr(k + strlen(pat), ':');
  if (!c) return v;
  c++;
  while (*c == ' ') c++;
  if (*c == '"') {
    v.isStr = true;
    v.p = c + 1;
    const char *e = strchr(v.p, '"');
    if (!e) return v;
    v.len = (int)(e - v.p);
    v.found = true;
  } else {
    v.p = c;
    const char *e = c;
    while (*e && *e != ',' && *e != '}' && *e != ']') e++;
    v.len = (int)(e - v.p);
    while (v.len > 0 && v.p[v.len-1] == ' ') v.len--;
    v.found = true;
  }
  return v;
}

static float jnum(const char *from, const char *key, float dflt) {
  JVal v = jfind(from, key);
  if (!v.found || v.isStr || v.len <= 0) return dflt;
  char buf[32];
  int n = v.len < 31 ? v.len : 31;
  memcpy(buf, v.p, n); buf[n] = 0;
  return atof(buf);
}

static bool jstr(const char *from, const char *key, char *out, int outLen, const char *dflt) {
  JVal v = jfind(from, key);
  if (!v.found || !v.isStr) {
    snprintf(out, outLen, "%s", dflt ? dflt : "");
    return false;
  }
  int n = v.len < outLen - 1 ? v.len : outLen - 1;
  memcpy(out, v.p, n); out[n] = 0;
  return true;
}

// ------------------------------------------------------------- iso/frac ----
// days from civil (Howard Hinnant) — no libc TZ dependency
static long daysFromCivil(long y, int m, int d) {
  y -= m <= 2;
  const long era = (y >= 0 ? y : y - 399) / 400;
  const long yoe = y - era * 400;
  const long doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + doe - 719468;
}

long isoToEpoch(const char *iso) {
  if (!iso || strlen(iso) < 19) return 0;
  int Y, M, D, h, m, s;
  if (sscanf(iso, "%d-%d-%dT%d:%d:%d", &Y, &M, &D, &h, &m, &s) != 6) return 0;
  return daysFromCivil(Y, M, D) * 86400L + h * 3600L + m * 60L + s;
}

void formatCountdown(int totalSec, char *out, int outLen) {
  if (totalSec < 0) { snprintf(out, outLen, "--"); return; }
  int h = totalSec / 3600, m = (totalSec % 3600) / 60;
  if (h >= 24) snprintf(out, outLen, "%dd %dh", h / 24, (h % 24));
  else if (h > 0) snprintf(out, outLen, "%dh %02dm", h, m);
  else snprintf(out, outLen, "%dm", m);
}

// live comet fraction: interpolates between companion fetches so the sweep moves
float sessionTimeFrac(const MeterData &d) {
  float f = d.sessionElapsedFrac;
  if (d.sessionResetEpoch > 0) {
    time_t now = time(nullptr);
    if (now > 100000) {
      long rem = (long)d.sessionResetEpoch - (long)now;
      if (rem < 0) rem = 0;
      float live = 1.0f - (float)rem / (float)SESSION_WINDOW_S;
      if (live >= 0 && live <= 1) f = live;    // clock-accurate when NTP is up
    }
  }
  if (f < 0) f = 0;
  if (f > 1) f = 1;
  return f;
}

void netInit() {
  configTime(0, 0, "time.cloudflare.com", "time.google.com");  // UTC
}

// Resolve the companion: mDNS service "ollama-meter._http" (advertising by
// companion.py), fallback to the NVS host field (user-typed IP).
static char s_host[48] = "";
static uint16_t s_port = 8615;
static bool s_resolved = false;

bool companionResolve(char *outHost, int outLen) {
  if (s_resolved) { snprintf(outHost, outLen, "%s", s_host); return true; }
  // 1) user override? ("auto" = mDNS)
  if (provHost() && provHost()[0] && strcmp(provHost(), "auto") != 0) {
    snprintf(s_host, sizeof(s_host), "%s", provHost());
    s_resolved = true;
    snprintf(outHost, outLen, "%s", s_host);
    return true;
  }
  // 2) mDNS auto-discover
  static MDNSResponder mdns;
  if (!MDNS.begin("meter-watch")) { MLOG("mdns begin failed"); return false; }
  int n = MDNS.queryService("ollama-meter", "http");
  if (n > 0) {
    IPAddress ip = MDNS.address(0);
    uint16_t port = MDNS.port(0);
    snprintf(s_host, sizeof(s_host), "%s", ip.toString().c_str());
    s_port = port;
    s_resolved = true;
    MLOG("mDNS found companion %s:%u", s_host, s_port);
    snprintf(outHost, outLen, "%s", s_host);
    return true;
  }
  MLOG("mDNS: no companion found");
  return false;
}

// -------------------------------------------------------------- fetch ----
static WiFiClient client;

static bool fetchUrl(const char *host, uint16_t port, const char *path,
                     char *buf, int bufLen) {
  HTTPClient http;
  char url[96];
  snprintf(url, sizeof(url), "http://%s:%u%s", host, port, path);
  if (!http.begin(client, url)) return false;
  http.setTimeout(6000);
  http.setConnectTimeout(4000);
  int code = http.GET();
  bool ok = false;
  if (code == 200) {
    String s = http.getString();
    int total = (int)s.length();
    if (total > bufLen - 1) total = bufLen - 1;
    memcpy(buf, s.c_str(), total);
    buf[total] = 0;
    ok = true;
  }
  http.end();
  return ok;
}

static bool parseSummary(const char *json, MeterData &d) {
  d.cloudAvail = strstr(json, "\"available\": true") != nullptr;
  d.sessionPct = jnum(json, "session_pct", -1.0f);
  d.weeklyPct  = jnum(json, "weekly_pct", -1.0f);
  d.sessionElapsedFrac = jnum(json, "session_elapsed_frac", -1.0f);

  {
    char iso[40];
    d.sessionResetEpoch = d.weeklyResetEpoch = 0;
    d.sessionResetMin = d.weeklyResetMin = -1;
    if (jstr(json, "session_reset_at", iso, sizeof(iso), "")) {
      d.sessionResetEpoch = isoToEpoch(iso);
      float rm = jnum(json, "session_reset_min", -1);
      d.sessionResetMin = rm < 0 ? -1 : (int)rm;
    }
    if (jstr(json, "weekly_reset_at", iso, sizeof(iso), "")) {
      d.weeklyResetEpoch = isoToEpoch(iso);
      float rm = jnum(json, "weekly_reset_min", -1);
      d.weeklyResetMin = rm < 0 ? -1 : (int)rm;
    }
  }
  jstr(json, "source", d.cloudSrc, sizeof(d.cloudSrc), "?");
  d.cloudAgeS = (int)jnum(json, "age_s", -1);

  d.serverOk = strstr(json, "\"server_ok\": true") != nullptr;
  jstr(json, "version", d.version, sizeof(d.version), "?");

  d.nLoaded = 0;
  const char *p = json;
  const char *loadedEnd = strstr(json, "models_installed");
  while (d.nLoaded < 3) {
    const char *nm = strstr(p, "\"name\"");
    if (!nm || (loadedEnd && nm > loadedEnd)) break;
    const char *vr = strstr(p, "\"size_vram\"");
    if (vr && vr < nm) { p = vr + 10; continue; }
    JVal v = jfind(nm, "name");
    if (!v.found || !v.isStr) break;
    LoadedModel &m = d.loaded[d.nLoaded++];
    int n = v.len < 23 ? v.len : 23;
    memcpy(m.name, v.p, n); m.name[n] = 0;
    m.vramMb = jnum(v.p, "size_vram", 0) / 1000000.0f;
    float us = jnum(v.p, "unload_in_s", -1);
    m.unloadInS = us < 0 ? -1 : (int)us;
    p = nm + 1;
  }
  d.modelsInstalled = (int)jnum(json, "models_installed", 0);

  d.todayReq = (int)jnum(json, "requests", 0);
  d.todayGen = (int)jnum(json, "generations", 0);
  d.todayErr = (int)jnum(json, "errors", 0);
  d.reqPerMin = jnum(json, "req_per_min", 0);
  return true;
}

bool netFetch(MeterData &g) {
  static char buf[3072];
  static char host[48];
  static uint16_t port = COMPANION_PORT;
  if (!companionResolve(host, sizeof(host))) {
    g.failCount++;
    if (g.failCount >= REBOOT_AFTER_FAILS) ESP.restart();
    return false;
  }
  if (!fetchUrl(host, port, SUMMARY_PATH, buf, sizeof(buf))) {
    g.failCount++;
    if (g.failCount >= REBOOT_AFTER_FAILS) ESP.restart();
    return false;
  }
  g.failCount = 0;
  bool changed = true;
  if (g.valid && g.rawLen > 0 && strncmp(buf, g.raw, sizeof(buf)) == 0) {
    changed = false;
  }
  MeterData tmp;
  memcpy(&tmp, &g, sizeof(MeterData));
  if (!parseSummary(buf, tmp)) return false;
  tmp.valid = true;
  tmp.fetchedMs = millis();
  tmp.rawLen = (int)strlen(buf);
  if (tmp.rawLen >= (int)sizeof(tmp.raw)) tmp.rawLen = sizeof(tmp.raw) - 1;
  memcpy(tmp.raw, buf, tmp.rawLen + 1);
  int cmp = g.valid ? memcmp(&tmp, &g, sizeof(MeterData)) : 1;
  memcpy(&g, &tmp, sizeof(MeterData));
  return changed || cmp != 0;
}