#!/usr/bin/env python3
"""v5: equal-width rings (two-tone), ALL stats inside the inner circle.
Left half: logo. Right half: full stat stack. Comet at session arc tip."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 466

src = Image.open(os.path.join(HERE, "assets", "lobe-dark.png")).convert("RGBA")
a = src.getchannel("A"); bbox = a.getbbox(); crop_a = a.crop(bbox)
lw, lh = crop_a.size
s = 104 / lh
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
         req=30.6, today=153, gen=110, err=6)

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED

def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)

def ring(d, cx, cy, rO, rI, pct, color):
    d.arc([cx-rO, cy-rO, cx+rO, cy+rO], 0, 360, fill=TRACK, width=rO-rI)
    if pct and pct > 0.3:
        d.arc([cx-rO, cy-rO, cx+rO, cy+rO], -90, -90+3.6*min(pct,100), fill=color, width=rO-rI)

def comet_at_tip(d, cx, cy, r, pct):
    ang = -90 + 3.6 * min(pct, 100)
    for a0, a1, col, w in [(-24,-16,FAINT,12),(-15,-7,DIM,12),(-6,0,INK,12)]:
        d.arc([cx-r-w/2, cy-r-w/2, cx+r+w/2, cy+r+w/2], ang+a0, ang+a1, fill=col, width=w)

def face(comet_ang=None):
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    cx, cy = 233, 228
    RW = 12   # EQUAL ring widths
    ring(d, cx, cy, 200, 200-RW, D["weekly"], CYAN)                  # outer: weekly
    ring(d, cx, cy, 182, 182-RW, D["session"], thresh(D["session"])) # inner: session
    comet_at_tip(d, cx, cy, 176, D["session"] if comet_ang is None else (comet_ang+90)/3.6)
    # ---- everything below is INSIDE the inner circle (r<=164) ----
    # left half: logo
    im.paste(logo, (cx-78-logo.width//2, cy-logo.height//2), logo)
    # right half: stat stack
    rx = cx - 4
    mono(d, (rx, cy-104), "SESSION", 14, DIM, anchor="lm")
    mono(d, (rx, cy-62),  f"{D['session']:.1f}%", 40, INK, anchor="lm")
    mono(d, (rx, cy-24),  f"resets {D['session_reset']}", 14, FAINT, anchor="lm")
    mono(d, (rx, cy+14),  f"{D['weekly']:.1f}% week", 17, CYAN, anchor="lm")
    mono(d, (rx, cy+44),  f"resets {D['week_reset']}", 14, FAINT, anchor="lm")
    mono(d, (rx, cy+80),  f"{D['req']:.1f} req/min", 15, CYAN, anchor="lm")
    mono(d, (rx, cy+106), f"{D['today']} today · {D['gen']} gen · {D['err']} err", 13, FAINT, anchor="lm")
    return im

tiles = [("A2.3 · hero", lambda: face(None)),
         ("comet 25%", lambda: face(-90+3.6*25)),
         ("comet 170°", lambda: face(-90+3.6*17))]
sheet = Image.new("RGB", (W*3+120, H+110), (15,17,25)); sd = ImageDraw.Draw(sheet)
lab = font(34)
for i,(name,fn) in enumerate(tiles):
    x,y = 30+i*(W+30), 50
    sd.text((x,y-42), name, font=lab, fill=INK)
    sheet.paste(fn(), (x,y))
    sd.rectangle([x-1,y-1,x+W,y+H], outline=(70,78,100), width=1)
sheet.save(os.path.join(HERE, "ui-contact-sheet-v5.png"))
tiles[0][1]().save(os.path.join(HERE, "tile-v5-hero.png"))
print("wrote v5")