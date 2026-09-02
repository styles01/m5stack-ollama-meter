# DESIGN LOCKED — v7 "Watch Face" (2026-09-01, James-approved)

**This is the final design. Do not redesign — implement exactly this.**
Reference implementation (ground truth): `render_variants_v7.py` in this folder.
Hero image: `tile-v7-hero.png` · all-state sheet: `ui-contact-sheet-v7.png`

## Concept
One watch face, no panes. Three concentric semantic rings, all stats inside
the inner circle, two-column inner card: logo+activity left, usage blocks right.

## Geometry (466×466, center 233,233)
| Element | Radii (out,in) | Width | Color |
|---|---|---|---|
| Weekly ring (outer) | 200–188 | 12px | **ALWAYS cyan** (86,208,226) |
| Session ring | 180–168 | 12px | threshold: green <70, amber 70–90, red ≥90 — (52,199,120)/(255,184,66)/(255,92,92) |
| Reset-timer ring | 158–152 | 6px | neutral: track (30,34,48), tail (122,130,150), head (200,206,222) |
| Inner safe radius | ≤146 | — | NOTHING (no text, no graphic) may exceed this |

Ring tracks: (30,34,48). Arcs start at 12 o'clock, sweep clockwise 3.6°/%.

## The comet = reset-timer (SEMANTIC, not decorative)
The thin ring fills as the session window ELAPSES; comet head (3 fading
segments, 6px) marks "now"; completes exactly at session reset. Neutral
white/grey only — never borrows stat colors.

## Color discipline (HARD RULES)
1. Cyan belongs to WEEKLY only: outer ring + the big weekly % number. Never used for any other text/element.
2. Session threshold color belongs to SESSION only: inner ring + big session % number.
3. All other text: white (240,242,248) / dim (122,130,150) / faint (84,92,114).
4. No dots, no legends — the color-matched big numbers ARE the legends.
5. Background (9,11,17).

## Inner-circle layout (all text ≤ r146 — verified by bleed checker)
Left column (x=159): Ollama logo 104px tall (LobeHub mark, recolored soft-white) top;
below: "30.6" (26px white) / "req/min" (12 dim) / "153 today" (12 faint) / "110 gen" (12 faint).
Right column (x=265, left-anchored):
- "SESSION" 12 dim · big "2.8%" 30px in session color · "resets 3h 04m" 12 faint
- "WEEKLY" 12 dim · big "53.8%" 30 CYAN · "resets 5d 03h" 12 faint

## Type & QA
- Monaco/mono everywhere (device: FreeMono 7b family).
- **Bleed checker**: every text bbox corner must be ≤146px from center —
  layout FAILS loudly otherwise (in render_variants_v7.py; port this check
  into any future layout changes).
- Data shown: session %, session reset, weekly %, weekly reset, req/min,
  today requests, generations. (Errors count optional; was dropped in v7 hero.)

## Logo
`assets/lobe-dark.png` (LobeHub lobe-icons Ollama, https://lobehub.com/icons/ollama),
alpha-cropped, recolored soft-white (245,247,252). Firmware 1-bit 128×128 header
already generated: `firmware/ollama-meter/ollama_logo.h` (regenerate via
render_variants_v2.py section 2 if logo changes).

## Colors are data-driven (not fixed pairs)
- Weekly ring/number: cyan at any level (it's the calm/info metric).
- Session ring/number: green <70 → amber 70–90 → red ≥90. At green, session is
  "cold"; cyan vs green disambiguate the rings; the big-number colors repeat
  their ring's color so mapping is unmistakable.