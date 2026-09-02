# ESP32 / M5Stack Build Infrastructure Inventory — /Volumes/1TBSSDClawd

*Generated 2026-09-01 · read-only survey · all paths verified on disk.*

---

## 1. ESP-IDF

| Item | Path / Version |
|---|---|
| ESP-IDF | `/Volumes/1TBSSDClawd/esp-idf` — **v5.5.4** (git tag `v5.5.4`, commit `735507283d5`, 2026-03-24) |
| Registration | `/Volumes/1TBSSDClawd/.espressif/idf-env.json` registers it as `esp-idf-v5.5`, target `esp32s3` |
| Python env | `/Volumes/1TBSSDClawd/.espressif/python_env/idf5.5_py3.9_env` (py3.9, IDF 5.5) |
| Entry point | `esp-idf/export.sh` + `esp-idf/tools/idf.py` (both present) |
| Constraint file | `/Volumes/1TBSSDClawd/.espressif/espidf.constraints.v5.5.txt` |

### Espressif toolchains (`/Volumes/1TBSSDClawd/.espressif/tools/`)
| Tool | Version |
|---|---|
| `xtensa-esp-elf` | esp-14.2.0_20260121 → `xtensa-esp-elf-gcc (crosstool-NG esp-14.2.0_20260121) 14.2.0` (verified by running `--version`) |
| `riscv32-esp-elf` | esp-14.2.0_20260121 → gcc 14.2.0 (verified) |
| `xtensa-esp-elf-gdb` | 16.3_20250913 |
| `openocd-esp32` | v0.12.0-esp32-20251215 |
| `esp32ulp-elf` | 2.38_20240113 |
| `esp-rom-elfs` | 20241011 |

Original installer archives also cached in `/Volumes/1TBSSDClawd/.espressif/dist/`.

**This is the exact ESP-IDF v5.5.4 that the official StackChan firmware README requires.**

---

## 2. PlatformIO

| Item | Path / Version |
|---|---|
| PlatformIO Core | `/Volumes/1TBSSDClawd/platformio-penv/bin/platformio` — **6.1.19** (verified: `pio --version`) |
| Data dir | `/Volumes/1TBSSDClawd/.platformio/` |
| Platform | `.platformio/platforms/espressif32` — **v55.03.311** (pioarduino fork; repo URL in platform.json is `pioarduino/platform-espressif32`) |
| Framework | `.platformio/packages/framework-arduinoespressif32` — **3.3.11** (arduino-esp32); separate `framework-arduinoespressif32-libs` pkg with per-target prebuilt libs (esp32/esp32s3/esp32c3/esp32c6/esp32p4/…) |
| Toolchain | `.platformio/packages/toolchain-xtensa-esp-elf` — **14.2.0+202****0121** (same esp-14.2.0_20260121 GCC as IDF) |
| Other packages | `tool-esptoolpy`, `tool-scons`, `tool-esp_install`, `tool-xtensa-esp-elf-gdb`, `contrib-piohome` |
| ESPHome | `platformio-penv/bin/esphome` (+ `esptool`, `espefuse`, `esp-coredump`, `pyserial-miniterm` in the same venv) |

Projects actually built with this PIO install:
- `/Volumes/1TBSSDClawd/stackchan-node/repos/plaipin-openclaw-stackchan/firmware/.pio/build/m5stack-cores3/` (built Aug 2026)
- `/Volumes/1TBSSDClawd/workspaces/crowdisplay/platformio.ini` (CrowPanel 7.0" ESP32-S3; pioarduino stable platform, `esp32-s3-devkitc-1`, LovyanGFX + LVGL 8.3.11)

---

## 3. Arduino CLI data (offloaded Arduino15)

**No arduino-cli binary found on the volume** (only a Homebrew bottle tarball: `/Volumes/1TBSSDClawd/Library/Caches/Homebrew/arduino-cli--1.5.1`, gzip; manifest for 1.5.1 alongside). But a full **offloaded data dir** exists:

`/Volumes/1TBSSDClawd/Library-offloads/Arduino15/` — recently touched (Sep 1 2026):

| Item | Detail |
|---|---|
| `arduino-cli.yaml` | Points `board_manager.additional_urls` at: `https://static-cdn.m5stack.com/resource/arduino/package_m5stack_index.json` **and** `https://espressif.github.io/arduino-esp32/package_esp32_index.json` |
| `package_m5stack_index.json` | M5Stack index, **latest platform "M5Stack 3.3.9"** (arch `esp32`); M5StopWatch board present in platforms 3.3.7 / 3.3.8 / 3.3.9 |
| `packages/esp32/hardware/esp32/3.3.11/` | **esp32 core 3.3.11 installed** (installed.json confirms; boards.txt has 4164 M5-prefixed entries incl. `m5stack_cores3`, `m5stack_tab5`, `m5stack_dial`…) |
| `packages/esp32/tools/` | `esp-x32/2601`, `esp-rv32/2601`, `esp32s3-libs/3.3.11` (full per-target libs), `esptool_py/5.3.1`, `xtensa-esp-elf-gdb/17.1_20260402`, `openocd-esp32` (20260424), `mklittlefs`, `mkspiffs` |
| `packages/arduino/hardware/avr/1.8.8` | Arduino AVR core 1.8.8 |
| `staging/packages/` | Install archives cached: `esp32-core-3.3.11.zip`, `esp32-libs-3.3.11.zip`, `esp32s3-libs-3.3.11.zip`, `xtensa-esp-elf-14.2.0_20260121-aarch64-apple-darwin.tar.gz`, `riscv32-esp-elf-14.2.0_20260121`, `esptool-v5.3.1-macos-arm64.tar.gz`, `dfu-util`, discovery tools |
| `staging/libraries/` | **`M5Unified-0.2.19.zip`**, **`M5GFX-0.2.26.zip`** (both downloaded Sep 1 2026), plus Arduino_BuiltIn/Ethernet/Firmata/Keyboard/LiquidCrystal/Mouse/SD/Servo/Stepper/TFT zips |
| `libraries/` | Only built-in Arduino libs installed (no M5 libs unpacked yet) |
| `library_index.json` | 57 MB, Aug 12 2026 |

**Not on the volume:** the installed `m5stack:esp32` platform itself (`packages/m5stack/` is absent) — the *index* is downloaded and the config already points at it, but the platform package itself was never installed here. (Context: `~/Library/Arduino15` on the home volume has esp32:esp32 3.3.11 + M5Unified 0.2.19 + M5GFX 0.2.26; the offload copy mirrors exactly that state + the M5Stack index.)

---

## 4. M5Stack board package — M5StopWatch

- **Index file:** `/Volumes/1TBSSDClawd/Library-offloads/Arduino15/package_m5stack_index.json`
  - Packager `m5stack`, platform name "M5Stack", architecture `esp32`
  - **Latest: 3.3.9** (3.3.8, 3.3.7 also carry the M5StopWatch board; 3.2.x and older do not)
  - M5StopWatch board listed as `{"name": "M5StopWatch"}` → FQBN `m5stack:esp32:m5stack_stopwatch` once installed
  - Tools the 3.3.9 platform depends on (m5stack-packaged): `esp-x32 2601`, `esp-rv32 2601`, `xtensa-esp-elf-gdb 16.3_20250913`, `openocd-esp32 v0.12.0-esp32-20251215`, `esptool_py 5.3.0`, `mkspiffs 0.2.3`, `mklittlefs 4.0.2-db0513a`, `esp32-libs 3.3.9` … `esp32s3-libs 3.3.9`, plus `arduino/dfu-util 0.11.0-arduino5`
  - Version parity note: m5stack 3.3.9 tool versions match what's already cached in `staging/packages/` for esp32 core 3.3.11 (xtensa-esp-elf 14.2.0_20260121, esptool 5.3.x, openocd 0.12.0-esp32-2026xxxx) — near-identical toolchain generation
- **No `boards.txt` containing `m5stack_stopwatch` exists on the volume** — the m5stack platform package itself is not installed anywhere here. `grep -rl m5stack_stopwatch` over the whole volume: zero hits in any boards.txt/ini/md.
- The stock `esp32:esp32` core 3.3.11 boards.txt (both the Arduino15 copy and the PlatformIO `framework-arduinoespressif32` copy) contains 4164 `m5stack_*` board IDs but **no stopwatch board** — the M5StopWatch only exists in the m5stack-packaged platform.

---

## 5. Libraries

| Location | Contents |
|---|---|
| `Library-offloads/Arduino15/staging/libraries/` | M5Unified **0.2.19** zip, M5GFX **0.2.26** zip (staged, not yet unpacked into `libraries/`) |
| `Library-offloads/Arduino15/libraries/` | built-ins only (no M5 libs installed on this volume) |
| `.platformio/packages/framework-arduinoespressif32/libraries/` | stock arduino-esp32 libs (no M5) |
| `/Volumes/1TBSSDClawd/ESP32-S3-Touch-LCD-7B/examples/Arduino/libraries/` | LVGL_v8.4.0.7z, LVGL_v9.5.0.7z (Waveshare 7B) |
| `stackchan-node/firmware/managed_components/` | ~60 IDF components: `espressif__esp-sr` (wake word), esp-dsp, esp_audio_codec, esp32-camera, xiaozhi-fonts, esp-wifi-connect, … |
| `stackchan-node/firmware/components/` | ArduinoJson, esp-now, mooncake, mooncake_log, smooth_ui_toolkit |
| `stackchan-node/repos/plaipin-openclaw-stackchan/firmware/lib/` | ESP8266AudioPlus, m5stack-avatar, README |
| plaipin `platformio.ini` lib_deps (cores3 env) | M5Unified @ 0.1.17, ESP8266Audio, ArduinoJson 7, stackchan-arduino (git), FastLED, YAMLDuino, esp32-camera, SimpleVox |

No TinyML/Edge Impulse trees; only `espressif__esp-sr` (WakeNet wake-word) inside the stackchan IDF build.

---

## 6. Past firmware projects

### 6.1 stackchan-node — `/Volumes/1TBSSDClawd/stackchan-node/` (the big one)
Stack-chan × OpenClaw × Hermes voice-agent client for **M5Stack CoreS3** (ESP32-S3, 16MB flash, ILI9342C).

- **`FLASHING-GUIDE.md`** (13.6 KB, Aug 20 2026) — hard-won CoreS3 flashing lessons. Key content:
  - CoreS3 = single USB-OTG port, flash **DIO mode** (bootloader switches to QIO), 16MB, no encryption/secure boot
  - Verify backups by magic bytes: `0xE9` at 0x0 (bootloader) and 0x10000 (app); `0xAA50` at 0x8000 (partition table)
  - otadata (0xe000, 0x2000) is a CRC'd 32-byte struct ×2 — never write raw select bytes; to force app0: `esptool.py --chip esp32s3 erase_region 0xe000 0x2000`
  - Modern partition subtypes only (ota_0=0x10, otadata=0x00, spiffs=0x82; old 0x40/0x20 are wrong)
  - CoreS3 16MB partition layout: nvs@0x9000, otadata@0xe000, app0@0x10000 (0x640000), app1@0x650000, spiffs@0xc90000, fr@0xfd0000, coredump@0xff0000 — **OTA-only, no factory partition; bootloader falls back to ota_0 when otadata invalid**
  - PlatformIO black-screen root cause: missing `-mfix-esp32-psram-cache-issue`, wrong board `esp32s3box` (should be `esp32-s3-devkitc-1`), M5Unified 0.1.17 vs M5GFX 0.2.27 mismatch
  - Flash offsets used by PIO/manual flashing: `0x0 bootloader.bin`, `0x8000 partitions.bin`, `0x10000 firmware.bin`; factory restore: `erase_flash` then single 0x0 write of the 16MB CDN image, `--flash_mode dio --flash_freq 80m --flash_size detect`
  - M5Burner CDN URLs for CoreS3 UIFlow2 factory images (v2.5.1 / v2.4.9 / v2.4.4)
- **`releases/v0.1/`** — ship-ready artifacts + `FLASH-v0.1.md`: `bootloader.bin`, `partition-table.bin`, `ota_data_initial.bin`, `stack-chan.bin`. Flash commands it documents:
  - ESP-IDF path: `export IDF_PATH=…; . $IDF_PATH/export.sh; cd firmware; idf.py set-target esp32s3; idf.py -p /dev/cu.usbmodemXXXX flash`
  - esptool path: `esptool.py --chip esp32s3 -p PORT -b 460800 --before=default_reset --after=hard_reset write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m 0x0 bootloader.bin 0x8000 partition-table.bin 0xd000 ota_data_initial.bin 0x20000 stack-chan.bin`
- **`firmware/`** — ESP-IDF project (based on official StackChan v1.4.3 / xiaozhi-esp32): `sdkconfig` with `CONFIG_IDF_TARGET="esp32s3"`, `dependencies.lock` requiring `idf >=5.5.2`, `partitions.csv`, full `build/` with prior build products (`stack-chan.bin`, bootloader, ota_data_initial), `managed_components/` (~60 esp-sr/audio/camera components)
- **`backups/`** — `backup_stackchan_stock.bin` (16MB full flash dump; guide warns its app partition at 0x10000 was **all 0xFF — not bootable**), `cores3_factory_uiflow2_v2.5.1.bin` (16MB UIFlow2 factory image), `firmware_cores3_patched_20260818_1809.bin` (2.5MB patched app), uncommitted patch + main.cpp
- **`repos/`** — `StackChan` (official firmware, README: ESP-IDF v5.5.4, `fetch_repos.py`, `idf.py build/flash`, host-side cmake tests), `StackChan-BSP`, `plaipin-openclaw-stackchan` (PlatformIO Arduino fork with `.pio/build/m5stack-cores3` build output), `stackchan-uiflow2` (MicroPython path), `esp-openclaw-node`, `zclaw`, `working-repos/` (Hermes-StackChan, stackchan-bluetooth-simple, stackchan-mcp, HeavenlyPointer, xiaozhi-esp32)
- **`ai-server/`** — Node.js companion server (WebSocket voice bridge) for the firmware
- **`analysis-*.md`** — deep dives incl. `analysis-platformio-issues.md` and uiflow2 analysis

### 6.2 esp32-panel — `/Volumes/1TBSSDClawd/esp32-panel/`
ESPHome project (not Arduino/IDF) for Waveshare ESP32-S3-Touch-LCD-7: `esp32-panel*.yaml`, `lvgl_redesign_*.yaml`, `common.yaml`, `secrets.yaml` (contains HA token), `HANDOFF_FLASH.md` (blocked-on-serial-port), `backup/factory_4MB.bin` (factory dump). Companion ESPHome is available via `platformio-penv/bin/esphome`.

### 6.3 ESP32-S3-Touch-LCD-7B — `/Volumes/1TBSSDClawd/ESP32-S3-Touch-LCD-7B/`
Waveshare 5" ESP32-S3 HMI repo: `examples/` (with Arduino libs: LVGL 8.4/9.5 7z), `firmware/` (~17 prebuilt demo .bin files: 01_GPIO … 16_lvgl_ui), `hardware/`.

### 6.4 crowdisplay — `/Volumes/1TBSSDClawd/workspaces/crowdisplay/`
PlatformIO (pioarduino platform URL, arduino framework) for Elecrow CrowPanel 7.0" ESP32-S3 800x480 + GT911; envs `display` + `bridge`; LovyanGFX, LVGL v8.3.11, ArduinoJson, MAX1704x; `partitions_4MB_app.csv`; prior build outputs.

### 6.5 Misc
- `/Volumes/1TBSSDClawd/open-source-research/OPENDRUMS/SOFTWARE/OPENDRUMS_V1.0_Arduino_Software.ino` — only .ino on the volume
- `/Volumes/1TBSSDClawd/repos/rtl9210-firmware` — NVMe bridge firmware (unrelated to ESP32)
- ESPHome community projects: `/Volumes/1TBSSDClawd/community-projects/{esphome_lvgl_hmi_garage, waveshare-esp32-s3-touch-lcd-7-esphome, waveshare-esp32s3-dashboard}`

---

## 7. Configs found

### arduino-cli config — `/Volumes/1TBSSDClawd/Library-offloads/Arduino15/arduino-cli.yaml`
```yaml
board_manager:
    additional_urls:
        - https://static-cdn.m5stack.com/resource/arduino/package_m5stack_index.json
        - https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

### PlatformIO projects
- `/Volumes/1TBSSDClawd/stackchan-node/repos/plaipin-openclaw-stackchan/firmware/platformio.ini` — envs `m5stack-core2` (platform espressif32@6.3.2), `m5stack-cores3` (board `esp32s3box` — flagged in FLASHING-GUIDE as wrong, use `esp32-s3-devkitc-1`; needs `-mfix-esp32-psram-cache-issue -DESP32S3 -DBOARD_HAS_PSRAM`, M5Unified ^0.2.20), `m5stack-cores3-llm`, `+aquestalk` variants; sd-updater/llm/realtime_api sections
- `/Volumes/1TBSSDClawd/workspaces/crowdisplay/platformio.ini` — pioarduino stable platform, esp32-s3-devkitc-1, qio_opi, 4MB, LovyanGFX/LVGL
- `/Volumes/1TBSSDClawd/stackchan-node/repos/working-repos/{HeavenlyPointer, stackchan-bluetooth-simple}/platformio.ini`

*(No other platformio.ini outside PlatformIO's own examples.)*

---

## 8. WHAT WE CAN USE FOR THE STOPWATCH METER BUILD

Target: M5StopWatch (ESP32-S3, 466×466 round AMOLED), FQBN `m5stack:esp32:m5stack_stopwatch`.

**Everything needed except one piece is already on disk.**

| Piece | Status | Where |
|---|---|---|
| M5Stack board index | ✅ downloaded | `Library-offloads/Arduino15/package_m5stack_index.json` (M5StopWatch in 3.3.7–3.3.9) |
| arduino-cli config pointing at M5Stack index | ✅ exists | `Library-offloads/Arduino15/arduino-cli.yaml` |
| esp32:esp32 core 3.3.11 | ✅ installed (offload copy) | `Library-offloads/Arduino15/packages/esp32/hardware/esp32/3.3.11` |
| Toolchains (xtensa/riscv GCC 14.2.0, esptool 5.3.x, gdb, openocd) | ✅ cached/installed ×3 locations | `.espressif/tools`, `.platformio/packages/toolchain-xtensa-esp-elf`, `Arduino15 staging/packages` |
| M5Unified 0.2.19 + M5GFX 0.2.26 | ✅ staged zips here; **installed on home volume** `~/Library/Arduino15` | offload `staging/libraries/*.zip` |
| **m5stack:esp32 platform package** | ❌ **NOT installed anywhere** (only the index) | would land in `packages/m5stack/…` on `core install` |
| ESP-IDF v5.5.4 + full toolchain | ✅ complete, registered, esp32s3 target | `/Volumes/1TBSSDClawd/esp-idf` + `.espressif/` |

### Option A — Arduino CLI with the M5Stack board package (direct FQBN match)
The m5stack index + config are sitting there; the only missing bit is the platform package download (m5stack 3.3.9 + its `esp-x32 2601` toolchain, which is **not** byte-identical to what's cached — `esp-x32`/`esp-rv32` are M5Stack's own packaging of the GCC 14.2 toolchain). Wiring it up on the home volume:

```bash
arduino-cli --config-file ~/Library/Arduino15/arduino-cli.yaml \
  core install m5stack:esp32          # downloads platform + m5stack tools
arduino-cli --config-file ~/Library/Arduino15/arduino-cli.yaml \
  compile --fqbn m5stack:esp32:m5stack_stopwatch <sketch>
```
The existing `arduino-cli.yaml` already carries both index URLs, so no config authoring is needed — point `--config-file` at it (or replicate the `additional_urls` block). M5Unified/M5GFX are already in `~/Library/Arduino15/libraries` (or installable from the staged zips on the SSD with `lib install --zip-path`).

Note: m5stack 3.3.9's `esp32-libs 3.3.9` are M5Stack-forked prebuilt libs; the cached `esp32s3-libs 3.3.11` (esp32 core) won't substitute inside the m5stack platform, so `core install` must fetch those ~small handful of packages once.

### Option B — ESP-IDF v5.5.4 (the stackchan precedent)
`/Volumes/1TBSSDClawd/esp-idf` is complete and registered (`idf-env.json` → esp32s3), and every StackChan build/flash doc on this volume drives it:

```bash
export IDF_PATH=/Volumes/1TBSSDClawd/esp-idf
source "$IDF_PATH/export.sh"        # uses .espressif python_env idf5.5_py3.9_env + tools
idf.py set-target esp32s3 && idf.py menuconfig && idf.py build flash
```
Use this if the stopwatch needs wake word/audio/LVGL-in-IDF or you want byte-for-byte parity with the working StackChan pipeline. Flash offsets convention (from FLASHING-GUIDE + releases/v0.1): bootloader 0x0, partition table 0x8000, otadata 0xd000/0xe000, app 0x10000 (CoreS3 layout) — check the StopWatch's own partition CSV when building.

### Recommendation
**Option A is the shortest path for the StopWatch meter**: the FQBN `m5stack:esp32:m5stack_stopwatch` only exists in the m5stack board package, M5Unified 0.2.19 + M5GFX 0.2.26 are already installed at `~/Library/Arduino15`, and the found `arduino-cli.yaml` already points at the right index — one `core install m5stack:esp32` command away. Fall back to Option B (esp-idf v5.5.4 at `/Volumes/1TBSSDClawd/esp-idf`) if Arduino-layer M5Unified proves insufficient for the round AMOLED (LVGL touch/rotation quirks) — the IDF tree, python env, and xtensa/riscv toolchains are already in place and proven by the stackchan-node builds. PlatformIO 6.1.19 also works as a third path (`pio run` with `platform = espressif32@55.03.311` + M5Unified libs), and the plaipin fork's build output proves the PIO + arduino-esp32 3.3.11 + M5Unified combo compiles fine on this machine.

**Hard constraint honored:** nothing was installed, updated, or downloaded during this survey; no arduino-cli binary exists on the volume to run non-mutating queries against.