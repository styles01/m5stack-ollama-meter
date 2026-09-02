#!/usr/bin/env bash
# flash.sh — build + flash the Ollama meter to the M5Stack StopWatch.
# Pre-flight checks included. PORT=... to override port detection.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ollama-meter"

FQBN="esp32:esp32:esp32s3:PartitionScheme=huge_app,PSRAM=opi,FlashSize=16M,USBMode=hwcdc,CDCOnBoot=cdc,DebugLevel=error"

ACLI="$(command -v arduino-cli || echo "/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli")"

echo "== pre-flight =="
# 1. companion reachable?
if curl -sf --max-time 5 http://localhost:8615/api/health >/dev/null 2>&1; then
  echo "  companion :8615 ........ OK"
else
  echo "  companion :8615 ...... DOWN  (start: cd companion && /usr/bin/python3 companion.py)"
fi
# 2. wifi creds set?
if grep -q "YOUR_WIFI_SSID" ollama-meter/config.h 2>/dev/null || grep -q "YOUR_WIFI_SSID" config.h 2>/dev/null; then
  echo "  WiFi creds ........... NOT SET (edit config.h WIFI_SSID/WIFI_PASS)"
  exit 1
else
  echo "  WiFi creds ........... set"
fi
# 3. device plugged in?
PORT="${PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT="$("$ACLI" board list --json 2>/dev/null | /usr/bin/python3 -c "
import json,sys
try:
    ports = json.load(sys.stdin)
    for p in ports:
        vid = (p.get('properties') or {}).get('vid','')
        if vid.lower() in ('0x303a','303a'):
            print(p['port']); break
except Exception: pass
")"
fi
if [[ -z "$PORT" ]]; then
  echo "  device ............... NOT FOUND (plug in StopWatch; check USB-C cable is data, not charge-only)"
  echo "  visible ports:"
  "$ACLI" board list 2>/dev/null || true
  exit 1
else
  echo "  device ............... $PORT"
fi

echo "== compile =="
"$ACLI" compile --fqbn "$FQBN" --build-path .build .

echo "== flash =="
"$ACLI" upload --fqbn "$FQBN" --port "$PORT" --input-dir .build

echo "== done. serial monitor: '$ACLI' monitor -p $PORT --config baudrate=115200"
echo "(device should join wifi, splash, then render live data — companion is serving it)"