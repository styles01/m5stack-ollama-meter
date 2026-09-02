#!/usr/bin/env python3
"""v4: A2 refined per James — labels off the rings, no divider line, no
breadcrumb arcs; comet pinned to the session-arc tip; straight mini bars at
bottom chord. One tile + a 3-frame comet strip."""
import math, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 466

src = Image.open(os.path.join(HERE, "assets", "lobe-dark.png")).convert("RGBA")
a = src.getchannel("A"); bbox = a.getbbox(); crop_a = a.crop(bbox)
lw, lh = crop_a.size
s = 100 / lh
logo = Image.new("RGBA", (int(lw*s), int(lh*s)), (0,0,0,0))
white = Image.new("RGBA", logo.size, (245,247,252,255))
logo.paste(white, (0,0), crop_a.resize(logo.size, Image.LANCZOS))

def font(sz):
    try: return ImageFont.truetype("/System/Library/Fonts/Monaco.dfont", sz)
    except Exception:
        try: return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", sz)
        except Exception: return ImageFont.load_default()

BG    = (9,11,17); INK=(240,242,248); DIM=(122,130,150); FAINT=(84,92,114)
TRACK = (30,34,48); CYAN=(86,208,226); GREEN=(52,199,120)
AMBER = (255,184,66); RED=(255,92,92)

D = dict(session=2.8, weekly=53.8, session_reset="3h 04m", week_reset="5d 03h",
         req=30.6, today=153, gen=110, err=6,
         hours=[1,0,0,0,0,0,0,0,2,4,9,14,11,18,22,16,25,31,28,44,61,88,121,153])

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED

def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)

def ring(d, cx, cy, rO, rI, pct, color):
    d.arc([cx-rO, cy-rO, cx+rO, cy+rO], 0, 360, fill=TRACK, width=rO-rI)
    if pct and pct > 0.3:
        d.arc([cx-rO, cy-rO, cx+rO, cy+rO], -90, -90+3.6*min(pct,100), fill=color, width=rO-rI)

def comet_at_tip(d, cx, cy, r, pct, color):
    """comet head exactly at the arc tip + short fading tail behind it"""
    ang = -90 + 3.6 * min(pct, 100)
    for k, (da, w, col) in enumerate([(-16, 6, FAINT), (-9, 7, DIM), (0, 8, INK)]):
        a0, a1 = ang + da, ang + da*0  if False else (ang if k==2 else ang+da+8)
    # simpler: three segments behind the tip
    segs = [(-22, -14, FAINT, 5), (-13, -6, DIM, 6), (-5, 0, INK, 8)]
    for a0, a1, col, w in segs:
        d.arc([cx-r-w/2, cy-r-w/2, cx+r+w/2, cy+r+w/2], ang+a0, ang+a1, fill=col, width=w)

def bottom_bars(d, vals):
    n = len(vals); bw, gap = 10, 3
    total = n*(bw+gap)-gap
    x0 = (W-total)//2; base = 458; mh = 24
    mx = max(max(vals), 1)
    for i, v in enumerate(vals[-n:]):
        h = max(2, int(v/mx*mh))
        col = CYAN if i >= n-2 else (40,62,100)
        d.rounded_rectangle([x0+i*(bw+gap), base-h, x0+i*(bw+gap)+bw, base], 2, fill=col)
    d.line([x0-6, base+4, x0+total+6, base+4], fill=(26,30,44), width=1)

def face(comet_ang_override=None):
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    cx, cy = 233, 218
    ring(d, cx, cy, 198, 189, D["weekly"], CYAN)
    ring(d, cx, cy, 179, 149, D["session"], thresh(D["session"]))
    # comet pinned to session arc tip
    ang = comet_ang_override if comet_ang_override is not None else -90 + 3.6*D["session"]
    r = 164
    for a0, a1, col, w in [(-22,-15,FAINT,5),(-14,-7,DIM,7),(-4,0,INK,8)]:
        d.arc([cx-r-w, cy-r-w, cx+r+w, cy+r+w], ang+a0, ang+a1, fill=col, width=w)
    # inner: vertical split — logo left, stats right
    im.paste(logo, (cx-72-logo.width//2, cy-logo.height//2), logo)
    rx = cx + 30
    mono(d, (rx, cy-46), "SESSION", 14, DIM, anchor="lm")
    mono(d, (rx, cy-10), f"{D['session']:.1f}%", 42, INK, anchor="lm")
    mono(d, (rx, cy+26), f"resets {D['session_reset']}", 14, FAINT, anchor="lm")
    mono(d, (rx, cy+64), f"WEEK {D['weekly']:.1f}%", 19, CYAN, anchor="lm")
    mono(d, (rx, cy+90), f"resets {D['week_reset']}", 14, FAINT, anchor="lm")
    # compass edges
    mono(d, (54, cy-2), f"{D['req']:.1f}", 26, CYAN)
    mono(d, (54, cy+28), "req/min", 14, FAINT)
    mono(d, (412, cy-2), f"{D['today']}", 26, INK)
    mono(d, (412, cy+28), f"{D['gen']} gen · {D['err']} err", 13, FAINT)
    # bottom chart + sync
    bottom_bars(d, D["hours"])
    mono(d, (233, 462), "", 10, FAINT)
    mono(d, (54, 444), "24h", 13, FAINT)
    mono(d, (412, 444), "sync 12s", 13, FAINT)
    return im

tiles = [("A2.2 · SPLIT V", lambda: face(None)),
         ("tip at 25%", lambda: face(25)),
         ("tip at 170°", lambda: face(170))]
sheet = Image.new("RGB", (W*3+120, H+120), (15,17,25)); sd = ImageDraw.Draw(sheet)
lab = font(34)
for i,(name,fn) in enumerate(tiles):
    x,y = 30+i*(W+30), 52
    sd.text((x,y-42), name, font=lab, fill=INK)
    sheet.paste(fn(), (x,y))
    sd.rectangle([x-1,y-1,x+W,y+H], outline=(70,78,100), width=1)
sheet.save(os.path.join(HERE, "ui-contact-sheet-v4.png"))
tiles[0][1]().save(os.path.join(HERE, "tile-v4-a22.png"))
print("wrote v4")