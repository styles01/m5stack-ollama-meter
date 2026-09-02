# M5Stack Ollama Usage Meter — Build Plan

**Owner:** Venus · **Created:** 2026-09-01 · **Design:** ✅ LOCKED (see design/DESIGN-LOCKED.md)
**Device:** M5Stack StopWatch (ESP32-S3R8, 16MB flash, 8MB octal PSRAM, 466×466 round AMOLED)
**Reference repo:** `reference-m5stack-claude-meter/` (CC0 — github.com/s-iwaki-d/m5stack-claude-meter)

## Architecture
```
[M5Stack StopWatch] --WiFi HTTP 10s--> [companion.py on Mac :8615]
                                         ├─ cloud: ollama.com/settings usage
                                         │   (OpenClaw cron JSON if fresh, else direct
                                         │    fetch w/ __Secure-session cookie from
                                         │    ~/.openclaw/workspace/command-center/data/)
                                         ├─ local: localhost:11434 /api/ps + /api/tags
                                         └─ activity: tails ~/.ollama/logs/server.log
                                             (GIN lines → today totals, req/min, 24h buckets)
```
Device = dumb renderer. Cookie NEVER lives on device. Companion payload: flat JSON
(cloud{available,session_pct,weekly_pct,session_reset_at,weekly_reset_at,age_s,source},
local{server_ok,version,loaded[{name,size_vram,unload_in_s}],models_installed},
activity{today{requests,generations,errors,req_per_min},hourly_today[]}). State file
`companion/state.json` persists hourly buckets + log offset across restarts.

## Milestones
- [x] M1: Reference repo analyzed (brief in findings/, CC0 license confirmed)
- [x] M2: HAR analyzed → direct-cookie fetch works, no JSON API on ollama.com (findings/ollama-har-analysis.md)
- [x] M3: OpenClaw prior work mapped (scraper files, stackchan lessons in findings/)
- [x] M4: Companion v1 RUNNING on :8615 — verified live: session 2.8%, weekly 53.8%, 30.6 req/min, hourly buckets, auto-choose direct-fetch when cron JSON stale
- [x] M5: Design LOCKED — v7 watch face (design/DESIGN-LOCKED.md + render_variants_v7.py)
- [x] M5.5: Toolchain solved ZERO-DOWNLOAD: HD Arduino15 esp32 core 3.3.11 + M5Unified 0.2.19 + M5GFX 0.2.26 (both natively support board_M5StopWatch), generic FQBN esp32:esp32:esp32s3:huge_app,PSRAM=opi,FlashSize=16M,USBMode=hwcdc,CDCOnBoot=cdc compiles clean (1.19MB, 37%). m5stack:esp32 board package NOT installed anywhere and NOT NEEDED. (findings/esp32-toolchain-inventory.md)
- [ ] M6: Firmware v7 watch-face implementation (replace current 3-pane ui.cpp with DESIGN-LOCKED spec; ollama_logo.h ready)
- [ ] M7: Host simulation — compile ui/net logic for macOS, render face from live companion JSON, compare against tile-v7-hero.png
- [ ] M8: Flash + verify on hardware (needs: plug in StopWatch, set WiFi SSID/pass in config.h; port detect VID 0x303a; reference FLASHING-GUIDE gotchas: --flash_mode dio, PSRAM=opi MANDATORY or black screen)

## Key facts (don't re-derive)
- ollama.com usage = server-rendered HTML only; regex "Session usage X% used" / "Weekly usage" / data-time attrs; cookie `__Secure-session` (long-lived, manual Chrome re-copy on expiry)
- Companion direct fetch: urllib GET + cookie header, verified live 200
- Reset semantics: session window ~5h (resets 3h04m from sample), weekly resets Monday 00:00Z; resetAt comes ISO from scrape
- Device NTP: configTime UTC; minutesToIso uses days-from-civil (no libc TZ)
- StopWatch gotchas from reference: PSRAM=opi mandatory (else pre-setup black screen); 24KB loop stack for TLS+JSON; USB CDC 115200; AMOLED burn-in → ±2px 10-min text jitter; canvas sprite 434KB must be PSRAM; red screen = sprite alloc failed
- Buttons: A=poll now, B=brightness cycle (80/140/200/40), C=(spare)
- arduino-cli on PATH is 1.5.1 brew; config points at SSD offload Arduino15 via symlink — do NOT "fix" paths

## HARD RULES (James)
- NO downloads/installs without explicit OK. Toolchain is complete on HD+SSD. (Violated once already 2026-09-01.)
- Design changes go through James: labeled contact sheets, he picks. Never auto-select.
- No text outside inner circle (bleed checker enforces), no decorative elements — every visual must be semantic.

## Open
- Companion autostart (launchd) — pending James OK
- Cookie expiry UX: companion sets cloud.available=false → face shows "re-auth needed" (design of that state not speced yet — ask James when it happens)