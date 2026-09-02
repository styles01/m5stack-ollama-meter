// provision.h — WiFi provisioning: NVS creds + captive-portal config mode.
// Pattern from M5Stack's official M5StopWatch-UserDemo (config_ap, MIT).
#pragma once
#include <cstdint>
#include <Arduino.h>   // String for WebServer args

bool provisionLoad();          // load creds from NVS -> getters below; true if ssid present
void provisionSave(const char *ssid, const char *pass, const char *host);
void provisionClear();
bool provisionHasCreds();

const char *provSsid();
const char *provPass();
const char *provHost();        // companion host (fallback: COMPANION_HOST)
uint16_t    provPort();        // companion port (fallback: COMPANION_PORT)

// Run the captive-portal config AP. BLOCKS until saved (then reboots) or
// timeoutMs elapses (returns false). Renders its own screens via ui.
void provisionRunPortal(uint32_t timeoutMs);