// provision.cpp — WiFi provisioning via captive portal (M5Stack UserDemo pattern).
// v2: async scan (never blocks the portal server), cached results, fixed JSON
// escaping, clearer screen (no QR), auto-retry on the phone page.
#include "provision.h"
#include "config.h"
#include "ui.h"
#include <M5Unified.h>
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <esp_wifi.h>
#include <esp_mac.h>
#include <cstring>
#include <cstdio>

// ---------------------------------------------------------------- storage --
static Preferences prefs;
static char s_ssid[33] = "";
static char s_pass[65] = "";
static char s_host[48] = "";

bool provisionLoad() {
  if (!prefs.begin("meter", true)) return false;
  String s = prefs.getString("ssid", "");
  String p = prefs.getString("pass", "");
  String h = prefs.getString("host", "");
  prefs.end();
  if (s.length() == 0) return false;
  snprintf(s_ssid, sizeof(s_ssid), "%s", s.c_str());
  snprintf(s_pass, sizeof(s_pass), "%s", p.c_str());
  snprintf(s_host, sizeof(s_host), "%s", h.length() ? h.c_str() : COMPANION_HOST);
  return true;
}

void provisionSave(const char *ssid, const char *pass, const char *host) {
  prefs.begin("meter", false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", pass);
  prefs.putString("host", host);
  prefs.end();
  snprintf(s_ssid, sizeof(s_ssid), "%s", ssid);
  snprintf(s_pass, sizeof(s_pass), "%s", pass);
  snprintf(s_host, sizeof(s_host), "%s", host);
}

void provisionClear() {
  prefs.begin("meter", false);
  prefs.clear();
  prefs.end();
  s_ssid[0] = s_pass[0] = 0;
  snprintf(s_host, sizeof(s_host), "%s", COMPANION_HOST);
}

bool provisionHasCreds() { return s_ssid[0] != 0; }
const char *provSsid() { return s_ssid; }
const char *provPass() { return s_pass; }
const char *provHost() { return s_host; }
uint16_t provPort() { return COMPANION_PORT; }

// ------------------------------------------------------------- portal UI ----
static const char PORTAL_HTML[] PROGMEM = R"HTML(<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ollama Meter Setup</title><style>
body{font-family:-apple-system,sans-serif;background:#0d0f16;color:#eef2f8;
     margin:0;padding:24px;max-width:420px;margin:0 auto}
h2{color:#56d0e2;font-weight:600;margin:0 0 4px}
.hint{color:#8a93a8;font-size:13px;margin-bottom:10px}
label{display:block;margin:14px 0 4px;font-size:13px;color:#8a93a8}
input{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;
      border:1px solid #2a3148;background:#161a26;color:#eef2f8;font-size:16px}
button{width:100%;margin-top:20px;padding:14px;border:0;border-radius:10px;
       background:#2f6bff;color:#fff;font-size:17px;font-weight:600}
button.mini{width:auto;margin:0;padding:8px 14px;font-size:14px;background:#23304d}
.net{padding:12px 8px;border-bottom:1px solid #222839;cursor:pointer;font-size:15px}
.net.sel{background:#23304d;border-radius:8px}
.ok{color:#34c778}.err{color:#ff5c5c}</style></head><body>
<h2>Ollama Meter</h2>
<div class="hint">Step 1: tap your network below. Step 2: type password. Step 3: Save.</div>
<label>WiFi networks <a href="#" onclick="toggleNets();return false" style="color:#56d0e2;font-size:12px" id="tgl">(hide)</a></label>
<div id="nets">scanning...</div>
<button class="mini" type="button" onclick="doScan()">re-scan</button>
<form onsubmit="return save(event)">
<label>Password</label>
<input id="pw" type="password" autocomplete="current-password">
<label>Companion host (auto-fills if found; else type your computer's IP)</label>
<input id="host" placeholder="auto (finding your computer...)">
<button>Save &amp; connect</button></form>
<div id="msg" style="margin-top:16px;min-height:22px"></div>
<script>
let chosen='';
function toggleNets(){
  const el=document.getElementById('nets');
  const t=document.getElementById('tgl');
  const h=el.style.display==='none';
  el.style.display=h?'':'none';
  t.textContent=h?'(hide)':'(show)';
}
async function doScan(){
  document.getElementById('nets').textContent='scanning...';
  for(let i=0;i<10;i++){
    const r=await fetch('/scan');const j=await r.json();
    if(j.nets && j.nets.length){render(j.nets);return;}
    if(!j.scanning){render(j.nets||[]);return;}
    await new Promise(z=>setTimeout(z,1500));
  }
  document.getElementById('nets').textContent='no networks yet - tap re-scan';
}
function render(list){
  const el=document.getElementById('nets');el.innerHTML='';
  if(!list.length){el.textContent='none found - tap re-scan';return;}
  list.sort((a,b)=>b.rssi-a.rssi).forEach(n=>{
    const d=document.createElement('div');d.className='net';
    d.textContent=n.ssid+(n.lock?'  \ud83d\udd12':'')+'   ('+n.rssi+' dBm)';
    d.onclick=()=>{chosen=n.ssid;
      document.querySelectorAll('.net').forEach(x=>x.classList.remove('sel'));
      d.classList.add('sel');};
    el.appendChild(d);});
}
async function save(e){e.preventDefault();
  const m=document.getElementById('msg');
  if(!chosen){m.className='err';m.textContent='tap a network first';return false;}
  const body='ssid='+encodeURIComponent(chosen)
            +'&pw='+encodeURIComponent(document.getElementById('pw').value)
            +'&host='+encodeURIComponent(document.getElementById('host').value);
  const r=await fetch('/save',{method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},body});
  const j=await r.json();m.className=j.status=='ok'?'ok':'err';m.textContent=j.message;
  return false;}
async function findCompanion(){
  try{
    const r=await fetch('http://ollama-meter.local:8615/api/host-info',{timeout:6000});
    const j=await r.json();
    if(j.ip){document.getElementById('host').value=j.ip;
      document.getElementById('host').placeholder='found: '+j.ip;
      document.getElementById('host').style.borderColor='#34c778';}
  }catch(e){document.getElementById('host').placeholder='type your computer IP';}
}
doScan();
findCompanion();
</script></body></html>)HTML";

// ----------------------------------------------------------- scan helpers ----
static String g_scanJson = "[]";

static String jsonEscape(const String &in) {
  String out;
  for (unsigned int i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '"' || c == '\\') { out += '\\'; out += c; }
    else if (c < 0x20) { out += ' '; }
    else out += c;
  }
  return out;
}

static void buildScanJson() {
  int n = WiFi.scanComplete();
  if (n < 0) return;
  String out = "{\"nets\":[";
  for (int i = 0; i < n; i++) {
    if (i) out += ",";
    out += "{\"ssid\":\"" + jsonEscape(WiFi.SSID(i)) + "\",\"rssi\":" +
           String(WiFi.RSSI(i)) + ",\"lock\":" +
           String(WiFi.encryptionType(i) != WIFI_AUTH_OPEN ? "true" : "false") + "}";
  }
  out += "]}";
  g_scanJson = out;
  WiFi.scanDelete();
}

static void kickScan() {
  WiFi.scanNetworks(true, false);   // async — portal server stays responsive
}

// ---------------------------------------------------------------- portal ----
void provisionRunPortal(uint32_t timeoutMs) {
  WiFi.mode(WIFI_AP_STA);

  uint8_t mac[6] = {};
  esp_read_mac(mac, ESP_MAC_WIFI_SOFTAP);
  static char apSsid[32];
  snprintf(apSsid, sizeof(apSsid), "M5Meter-%02X%02X", mac[4], mac[5]);

  WiFi.softAP(apSsid);                    // open AP
  IPAddress apIp = WiFi.softAPIP();       // 192.168.4.1
  MLOG("portal AP up: %s at %s", apSsid, apIp.toString().c_str());

  DNSServer dns;
  dns.start(53, "*", apIp);

  WebServer server(80);
  bool haveSave = false;

  server.on("/", HTTP_GET, [&]() {
    MLOG("portal page -> %s", server.client().remoteIP().toString().c_str());
    server.send_P(200, "text/html", PORTAL_HTML);
  });
  server.on("/scan", HTTP_GET, [&]() {
    int st = WiFi.scanComplete();
    MLOG("/scan -> %s (state %d)", server.client().remoteIP().toString().c_str(), st);
    if (st >= 0) {
      buildScanJson();
      kickScan();                         // fresh data for the next poll
      server.send(200, "application/json", g_scanJson);
    } else if (st == WIFI_SCAN_RUNNING) {
      String out = "{\"nets\":" + g_scanJson + ",\"scanning\":true}";
      server.send(200, "application/json", out);
    } else {
      kickScan();
      server.send(200, "application/json", "{\"nets\":[],\"scanning\":true}");
    }
  });
  server.on("/save", HTTP_POST, [&]() {
    // form-encoded (WebServer decodes args) — survives quotes/backslashes in
    // passwords and SSIDs, unlike the previous hand-rolled JSON parser
    String ssid = server.arg("ssid");
    String pw   = server.arg("pw");
    String host = server.arg("host");
    if (ssid.length() == 0) {
      server.send(400, "application/json",
                  "{\"status\":\"err\",\"message\":\"tap a network first\"}");
      return;
    }
    if (host.length() == 0) {
      host = "auto";                    // empty = mDNS auto-discovery
    }
    provisionSave(ssid.c_str(), pw.c_str(), host.c_str());
    haveSave = true;
    MLOG("creds saved: ssid=%s host=%s -> rebooting", ssid.c_str(), host.c_str());
    server.send(200, "application/json",
                "{\"status\":\"ok\",\"message\":\"saved. watch is rebooting...\"}");
  });
  server.onNotFound([&]() {
    server.sendHeader("Location", "http://" + apIp.toString() + "/", true);
    server.send(302, "text/plain", "");
  });
  server.begin();

  kickScan();
  MLOG("portal ready, waiting for phone...");
  M5LcdConfigScreen(apSsid, apIp.toString().c_str());

  uint32_t t0 = millis();
  // timeoutMs == 0 -> run until saved (portal is the resting state when
  // no creds exist; never fall through to a doomed WiFi join)
  while (!haveSave && (timeoutMs == 0 || millis() - t0 < timeoutMs)) {
    dns.processNextRequest();
    server.handleClient();
    delay(10);
  }

  dns.stop();
  server.stop();
  WiFi.scanDelete();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_OFF);

  if (haveSave) {
    M5LcdMessage("Saved", "Rebooting...");
    delay(1200);
    ESP.restart();
  }
}