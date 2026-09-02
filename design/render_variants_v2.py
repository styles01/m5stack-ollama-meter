#!/usr/bin/env python3
"""v2: one-face watch-style layouts — Ollama logo center + ALL stats, Monaco,
comet-ring animation. Extracts the real logo from /Applications/Ollama.app
locally (no downloads), generates the firmware 1-bit header, renders 3 labeled
variants + animation-frame strip as a contact sheet."""
import math, os, subprocess, glob
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 466

# ---------------- 1. logo: LobeHub official Ollama icon (user-provided source)
logo_rgba = None
_lobe = os.path.join(HERE, "assets", "lobe-dark.png")
if os.path.exists(_lobe):
    src = Image.open(_lobe).convert("RGBA")
    a = src.getchannel("A")
    bbox = a.getbbox()
    crop_a = a.crop(bbox)
    lw, lh = crop_a.size
    s = min(380 / lw, 380 / lh)
    crop_a = crop_a.resize((int(lw * s), int(lh * s)), Image.LANCZOS)
    logo_rgba = Image.new("RGBA", crop_a.size, (0, 0, 0, 0))
    white = Image.new("RGBA", crop_a.size, (245, 247, 252, 255))
    logo_rgba.paste(white, (0, 0), crop_a)   # recolor to soft white for dark face
    print("logo: lobe-dark.png ->", logo_rgba.size)
else:
    raise SystemExit("assets/lobe-dark.png missing")

# ---------------- 2. firmware 1-bit header (128x128) -----------------------
bit = crop_a.resize((128, 128), Image.LANCZOS).point(lambda v: 255 if v > 128 else 0)
px = bit.load()
rows = []
for y in range(128):
    row = []
    for xb in range(16):
        b = 0
        for k in range(8):
            x = xb * 8 + k
            if x < 128 and px[x, y]:
                b |= 0x80 >> k
        row.append(b)
    rows.append(row)
flat = [b for r in rows for b in r]
hdr = ["// ollama_logo.h — auto-generated from /Applications/Ollama.app icon",
       "// 128x128 1-bit llama silhouette (MSB first). Draw with drawBitmap().",
       "#pragma once",
       "#include <pgmspace.h>",
       "#define LOGO_W 128",
       "#define LOGO_H 128",
       "static const uint8_t ollama_logo_bits[LOGO_H * (LOGO_W / 8)] PROGMEM = {"]
for i in range(0, len(flat), 12):
    hdr.append("  " + ", ".join("0x%02X" % b for b in flat[i:i+12]) + ",")
hdr.append("};")
os.makedirs(os.path.join(HERE, "..", "firmware", "ollama-meter"), exist_ok=True)
with open(os.path.join(HERE, "..", "firmware", "ollama-meter", "ollama_logo.h"), "w") as f:
    f.write("\n".join(hdr))
print("wrote ollama_logo.h (%d bytes payload)" % len(flat))

# ---------------- 3. fonts --------------------------------------------------
def font(sz):
    for p, i in (("/System/Library/Fonts/Monaco.dfont", 0),
                 ("/System/Library/Fonts/Menlo.ttc", 0),
                 ("/System/Library/Fonts/Helvetica.ttc", 0)):
        try:
            return ImageFont.truetype(p, sz, index=i)
        except Exception:
            continue
    return ImageFont.load_default()

def font_sans(sz):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", sz)
    except Exception:
        return font(sz)

# ---------------- 4. palette / helpers --------------------------------------
BG     = (9, 11, 17)
INK    = (240, 242, 248)
DIM    = (122, 130, 150)
FAINT  = (74, 82, 104)
TRACK  = (30, 34, 48)
CLOUD  = (112, 138, 255)
CYAN   = (86, 208, 226)
GREEN  = (52, 199, 120)
AMBER  = (255, 184, 66)
CARD   = (24, 28, 40)

D = dict(session=2.8, weekly=53.8, reset="5d 03h", req=30.6, today="153", gen="110",
         err="6", model="glm-5.3-flash:cloud", vram="3.1 GB", unload="14:52",
         installed=20,
         hours=[1,0,0,0,0,0,0,0,2,4,9,14,11,18,22,16,25,31,28,44,61,88,121,153])

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else (255, 92, 92)

def arc_ring(d, cx, cy, r, w, pct, color, track=True, start=-90, comet=None):
    box = [cx - r, cy - r, cx + r, cy + r]
    if track:
        d.arc(box, 0, 360, fill=TRACK, width=w)
    if pct and pct > 0.3:
        sweep = 3.6 * min(pct, 100)
        d.arc(box, start, start + sweep, fill=color, width=w)
    if comet is not None:
        d.arc(box, comet - 8, comet, fill=INK, width=w)

def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)

def paste_logo(im, cx, cy, scale=1.0):
    l = logo_rgba
    if scale != 1.0:
        l = l.resize((max(1, int(l.width * scale)), max(1, int(l.height * scale))), Image.LANCZOS)
    im.paste(l, (cx - l.width // 2, cy - l.height // 2), l)

def curved_bars(d, cx, cy, r0, vals, maxv, w=7):
    n = len(vals)
    span = 150
    step = span / (n - 1)
    for i, v in enumerate(vals):
        ang = 90 - span / 2 + i * step
        h = 8 + (v / maxv) * 52 if v else 3
        a0 = ang - w * 0.55
        a1 = ang + w * 0.55
        col = CYAN if i >= n - 3 else (44, 74, 116)
        d.arc([cx - r0 - h, cy - r0 - h, cx + r0 + h, cy + r0 + h], a0, a1, fill=col, width=5)

# ---------------- 5. variants ------------------------------------------------
def v_A():
    """WATCH FACE — logo center in session ring, weekly outer, stats at compass
    points, curved 24h bars along bottom arc, comet animation."""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    cx, cy = 233, 210
    arc_ring(d, cx, cy, 196, 8, D["weekly"], CYAN)                 # outer: weekly
    arc_ring(d, cx, cy, 166, 26, D["session"], thresh(D["session"]),
             comet=118)                                            # inner: session + comet
    paste_logo(im, cx, cy - 6, 0.62)
    mono(d, (cx, cy + 92), f"{D['session']:.1f}%", 40, INK)
    mono(d, (cx, cy - 168), "WEEKLY", 17, DIM)
    mono(d, (cx, cy - 146), f"{D['weekly']:.0f}%", 26, CYAN)
    mono(d, (cx - 148, cy + 6), "REQ/MIN", 16, DIM)
    mono(d, (cx - 148, cy + 30), f"{D['req']:.1f}", 26, CYAN)
    mono(d, (cx - 146, cy + 78), f"reset {D['reset']}", 16, FAINT)
    mono(d, (cx + 148, cy + 6), "TODAY", 16, DIM)
    mono(d, (cx + 148, cy + 30), f"{D['today']} req", 22, INK)
    mono(d, (cx + 148, cy + 56), f"{D['gen']} gen · {D['err']} err", 15, FAINT)
    mono(d, (cx + 148, cy + 80), f"sync 12s", 15, FAINT)
    curved_bars(d, cx, cy, 88, D["hours"][-20:], max(D["hours"]))
    return im

def v_B():
    """LOGO + LEDGER — logo top-center in ring, two ledger columns below,
    straight bars bottom."""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    cx = 233
    arc_ring(d, cx, 122, 96, 20, D["session"], thresh(D["session"]), comet=52)
    paste_logo(im, cx, 118, 0.40)
    mono(d, (cx + 128, 92), "SESSION", 16, DIM)
    mono(d, (cx + 128, 120), f"{D['session']:.1f}%", 34, INK)
    mono(d, (cx + 128, 152), f"weekly {D['weekly']:.0f}%", 17, CYAN)
    d.rounded_rectangle([40, 238, 426, 242], 1, fill=(36, 40, 56))
    L = [("session", f"{D['session']:.1f}%"), ("weekly", f"{D['weekly']:.1f}%"),
         ("resets", D["reset"]), ("req/min", f"{D['req']:.1f}")]
    R = [("model", D["model"]), ("vram", D["vram"]),
         ("unloads", D["unload"]), ("installed", f"{D['installed']} models")]
    y = 262
    for (k1, v1), (k2, v2) in zip(L, R):
        mono(d, (44, y), k1, 16, FAINT, anchor="lm")
        mono(d, (44 + 96, y), v1, 18, INK, anchor="lm")
        mono(d, (244, y), k2, 16, FAINT, anchor="lm")
        mono(d, (244 + 88, y), v2, 18, INK, anchor="lm")
        y += 38
    base, mh, bw, gap, x0 = 452, 74, 12, 3.4, 44
    mx = max(max(D["hours"]), 1)
    for i, v in enumerate(D["hours"][-22:]):
        h = max(2, int(v / mx * mh))
        d.rounded_rectangle([x0 + i * (bw + gap), base - h, x0 + i * (bw + gap) + bw, base],
                            2, fill=CYAN if i >= 19 else (44, 74, 116))
    return im

def v_C():
    """HALO — giant halo ring = session, logo floats center, weekly + stats on
    lower card, curved bars arc top."""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    cx, cy = 233, 168
    arc_ring(d, cx, cy, 140, 12, D["session"], thresh(D["session"]), comet=200)
    paste_logo(im, cx, cy, 0.5)
    mono(d, (cx, cy + 128), f"{D['session']:.1f}% session", 22, INK)
    mono(d, (cx, cy + 156), f"weekly {D['weekly']:.1f}%  ·  resets {D['reset']}", 17, CYAN)
    curved_bars(d, cx, 168, 158, D["hours"][-14:], max(D["hours"]))
    d.rounded_rectangle([40, 340, 426, 440], 16, fill=CARD)
    mono(d, (58, 362), f"{D['model']}", 19, INK, anchor="lm")
    mono(d, (58, 390), f"{D['vram']} VRAM", 16, DIM, anchor="lm")
    mono(d, (58, 414), f"unloads in {D['unload']}", 16, AMBER, anchor="lm")
    mono(d, (408, 362), f"{D['req']:.1f}", 30, CYAN, anchor="rm")
    mono(d, (408, 392), "req/min", 15, FAINT, anchor="rm")
    mono(d, (408, 414), f"{D['today']} req · {D['gen']} gen", 15, FAINT, anchor="rm")
    return im

# animation frames strip (variant A comet at 3 positions)
def frames_strip():
    fr = Image.new("RGB", (W, 120), BG); d = ImageDraw.Draw(fr)
    mono(d, (18, 18), "COMET ANIMATION (3 frames)", 20, DIM, anchor="lm")
    for i, ang in enumerate([30, 150, 270]):
        ox = 90 + i * 140
        arc_ring(d, ox, 74, 44, 8, D["session"], thresh(D["session"]),
                 track=True, comet=ang)
        mono(d, (ox, 74), "42%", 15, INK)
    return fr

tiles = [("A · WATCH FACE", v_A), ("B · LOGO + LEDGER", v_B), ("C · HALO", v_C)]
sheet = Image.new("RGB", (W * 3 + 120, H + 190), (15, 17, 25))
sd = ImageDraw.Draw(sheet)
lab = font_sans(38)
for i, (name, fn) in enumerate(tiles):
    x, y = 30 + i * (W + 30), 58
    sd.text((x, y - 46), name, font=lab, fill=INK)
    sheet.paste(fn(), (x, y))
    sd.rectangle([x - 1, y - 1, x + W, y + H], outline=(70, 78, 100), width=1)
sheet.paste(frames_strip(), (30, H + 76))
sheet.save(os.path.join(HERE, "ui-contact-sheet-v2.png"))
v_A().save(os.path.join(HERE, "tile-v2-a.png"))
v_B().save(os.path.join(HERE, "tile-v2-b.png"))
v_C().save(os.path.join(HERE, "tile-v2-c.png"))
print("wrote ui-contact-sheet-v2.png + tiles")