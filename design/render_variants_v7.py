#!/usr/bin/env python3
"""v7: outer ring ALWAYS cyan (= weekly, calm/info), inner ring = session
threshold color (the alarm). Big % numbers color-matched to their rings —
no swatch dots. Bleed check still enforced."""
import math, os
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
TRACK = (30,34,48); CYAN=(86,208,226)
GREEN=(52,199,120); AMBER=(255,184,66); RED=(255,92,92)
NEUTRAL=(200,206,222)

CX, CY = 233, 233
R_WEEK = (200, 188); R_SESS = (180, 168); R_TIME = (158, 152)
SAFE_R = 146

viol = []
def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)
    bb = d.textbbox(xy, s, font=font(sz), anchor=anchor)
    for (x, y) in [(bb[0],bb[1]),(bb[2],bb[1]),(bb[0],bb[3]),(bb[2],bb[3])]:
        if math.hypot(x-CX, y-CY) > SAFE_R:
            viol.append((s[:18], int(math.hypot(x-CX, y-CY))))

def ring(d, rO, rI, pct, color):
    d.arc([CX-rO, CY-rO, CX+rO, CY+rO], 0, 360, fill=TRACK, width=rO-rI)
    if pct and pct > 0.3:
        d.arc([CX-rO, CY-rO, CX+rO, CY+rO], -90, -90+3.6*min(pct,100), fill=color, width=rO-rI)

def face(session_pct, weekly_pct, time_frac, session_reset="3h 04m", week_reset="5d 03h"):
    global viol; viol = []
    def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED
    sess_col = thresh(session_pct)
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    ring(d, *R_WEEK, weekly_pct, CYAN)            # weekly: ALWAYS cyan
    ring(d, *R_SESS, session_pct, sess_col)       # session: threshold color
    # reset-timer ring (neutral) with comet head
    d.arc([CX-R_TIME[0], CY-R_TIME[0], CX+R_TIME[0], CY+R_TIME[0]], 0, 360, fill=TRACK, width=R_TIME[0]-R_TIME[1])
    ang = -90 + 360*max(0.01, time_frac)
    rr = (R_TIME[0]+R_TIME[1])/2
    for a0,a1,col,w in [(-26,-16,(60,66,88),6),(-15,-6,DIM,6),(-5,0,NEUTRAL,6)]:
        d.arc([CX-rr-w/2, CY-rr-w/2, CX+rr+w/2, CY+rr+w/2], ang+a0, ang+a1, fill=col, width=w)
    # left: logo + activity
    lx = CX - 74
    im.paste(logo, (lx-logo.width//2, CY-62-logo.height//2), logo)
    mono(d, (lx, CY+24), "30.6", 26, INK)
    mono(d, (lx, CY+50), "req/min", 12, DIM)
    mono(d, (lx, CY+74), "153 today", 12, FAINT)
    mono(d, (lx, CY+96), "110 gen", 12, FAINT)
    # right: session + weekly, big numbers color-matched to rings
    rx = CX + 32
    mono(d, (rx+12, CY-98), "SESSION", 12, DIM, anchor="lm")
    mono(d, (rx, CY-64), f"{session_pct:.1f}%", 30, sess_col, anchor="lm")
    mono(d, (rx, CY-36), f"resets {session_reset}", 12, FAINT, anchor="lm")
    mono(d, (rx+12, CY-2), "WEEKLY", 12, DIM, anchor="lm")
    mono(d, (rx, CY+32), f"{weekly_pct:.1f}%", 30, CYAN, anchor="lm")
    mono(d, (rx, CY+60), f"resets {week_reset}", 12, FAINT, anchor="lm")
    return im

def face_safe(*a, **k):
    name = k.pop("name", "tile")
    im = face(*a, **k)
    print(f"{name}: bleed-check {'PASS' if not viol else 'FAIL ' + str(viol)}")
    return im

# hero: both green-ish + one alarm state + comet positions
tiles = [
    ("HERO · calm",   dict(session_pct=2.8,  weekly_pct=53.8, time_frac=0.35)),
    ("session amber", dict(session_pct=74.2, weekly_pct=53.8, time_frac=0.75)),
    ("both hot",      dict(session_pct=91.5, weekly_pct=87.0, time_frac=0.99,
                           session_reset="0h 12m", week_reset="1d 06h")),
]
sheet = Image.new("RGB", (W*3+120, H+110), (15,17,25)); sd = ImageDraw.Draw(sheet)
lab = font(34)
for i,(name,kw) in enumerate(tiles):
    im = face_safe(name=name, **kw)
    x,y = 30+i*(W+30), 50
    sd.text((x,y-42), name, font=lab, fill=INK)
    sheet.paste(im, (x,y))
    sd.rectangle([x-1,y-1,x+W,y+H], outline=(70,78,100), width=1)
sheet.save(os.path.join(HERE, "ui-contact-sheet-v7.png"))
face_safe(name="hero", **tiles[0][1]).save(os.path.join(HERE, "tile-v7-hero.png"))
print("wrote v7")