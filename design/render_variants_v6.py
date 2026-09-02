#!/usr/bin/env python3
"""v6: semantic rings + strict color discipline + PROVEN no-bleed.
Rings (outer->inner): WEEKLY usage (12px, threshold color), SESSION usage
(12px, threshold color), reset-timer (6px, neutral; comet head = time elapsed
toward session reset). All text inside inner circle; script verifies every
text bbox fits inside r=146 with margin — prints PASS/FAIL per tile."""
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
TRACK = (30,34,48); GREEN=(52,199,120); AMBER=(255,184,66); RED=(255,92,92)
NEUTRAL=(200,206,222)

D = dict(session=2.8, weekly=53.8, session_reset="3h 04m", week_reset="5d 03h",
         req=30.6, today=153, gen=110, err=6)

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED

# geometry
CX, CY = 233, 233
R_WEEK = (200, 188)     # outer 12px
R_SESS = (180, 168)     # 12px
R_TIME = (158, 152)     # 6px neutral reset-progress
SAFE_R = 146            # nothing (text) may exceed this radius

violations = []
def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)
    bb = d.textbbox(xy, s, font=font(sz), anchor=anchor)
    for (x, y) in [(bb[0],bb[1]),(bb[2],bb[1]),(bb[0],bb[3]),(bb[2],bb[3])]:
        r = math.hypot(x-CX, y-CY)
        if r > SAFE_R:
            viol.append((s[:18], int(r)))

def ring(d, rO, rI, pct, color):
    d.arc([CX-rO, CY-rO, CX+rO, CY+rO], 0, 360, fill=TRACK, width=rO-rI)
    if pct and pct > 0.3:
        d.arc([CX-rO, CY-rO, CX+rO, CY+rO], -90, -90+3.6*min(pct,100), fill=color, width=rO-rI)

def face(time_frac):
    """time_frac: 0..1 elapsed toward session reset (comet head position)."""
    global viol; viol = []
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    ring(d, *R_WEEK, D["weekly"], thresh(D["weekly"]))
    ring(d, *R_SESS, D["session"], thresh(D["session"]))
    # reset-timer ring: neutral, comet head = elapsed fraction
    d.arc([CX-R_TIME[0], CY-R_TIME[0], CX+R_TIME[0], CY+R_TIME[0]], 0, 360, fill=TRACK, width=R_TIME[0]-R_TIME[1])
    ang = -90 + 360*max(0.01, time_frac)
    rT = (R_TIME[0]+R_TIME[1])/2
    for a0,a1,col,w in [(-26,-16,(60,66,88),6),(-15,-6,DIM,6),(-5,0,NEUTRAL,6)]:
        d.arc([CX-rT-w, CY-rT-w, CX+rT+w, CY+rT+w], ang+a0, ang+a1, fill=col, width=6) if False else None
    for a0,a1,col,w in [(-26,-16,(60,66,88),6),(-15,-6,DIM,6),(-5,0,NEUTRAL,6)]:
        rr = (R_TIME[0]+R_TIME[1])/2
        d.arc([CX-rr-w/2, CY-rr-w/2, CX+rr+w/2, CY+rr+w/2], ang+a0, ang+a1, fill=col, width=w)

    # ---- left column: logo + activity (all centered, inside SAFE_R) ----
    lx = CX - 74
    im.paste(logo, (lx-logo.width//2, CY-62-logo.height//2), logo)
    mono(d, (lx, CY+24), f"{D['req']:.1f}", 26, INK)
    mono(d, (lx, CY+50), "req/min", 12, DIM)
    mono(d, (lx, CY+74), f"{D['today']} today", 12, FAINT)
    mono(d, (lx, CY+96), f"{D['gen']} gen", 12, FAINT)

    # ---- right column: session + weekly blocks with swatch dots ----
    rx = CX + 32
    def swatch(y, col):
        d.ellipse([rx-8, y-3, rx-2, y+3], fill=col)
    mono(d, (rx+12, CY-98), "SESSION", 12, DIM, anchor="lm")
    swatch(CY-98, thresh(D["session"]))
    mono(d, (rx, CY-64), f"{D['session']:.1f}%", 30, INK, anchor="lm")
    mono(d, (rx, CY-36), f"resets {D['session_reset']}", 12, FAINT, anchor="lm")
    mono(d, (rx+12, CY-2), "WEEKLY", 12, DIM, anchor="lm")
    swatch(CY-2, thresh(D["weekly"]))
    mono(d, (rx, CY+32), f"{D['weekly']:.1f}%", 30, INK, anchor="lm")
    mono(d, (rx, CY+60), f"resets {D['week_reset']}", 12, FAINT, anchor="lm")
    return im

def face_safe(time_frac, name):
    im = face(time_frac)
    status = "PASS" if not viol else f"FAIL {viol}"
    print(f"{name}: bleed-check {status}")
    return im

tiles = [("HERO · t=35%", 0.35), ("t=75%", 0.75), ("t=99%", 0.99)]
sheet = Image.new("RGB", (W*3+120, H+110), (15,17,25)); sd = ImageDraw.Draw(sheet)
lab = font(34)
imgs = []
for i,(name,tf) in enumerate(tiles):
    im = face_safe(tf, name)
    x,y = 30+i*(W+30), 50
    sd.text((x,y-42), name, font=lab, fill=INK)
    sheet.paste(im, (x,y))
    sd.rectangle([x-1,y-1,x+W,y+H], outline=(70,78,100), width=1)
sheet.save(os.path.join(HERE, "ui-contact-sheet-v6.png"))
face_safe(0.35, "hero").save(os.path.join(HERE, "tile-v6-hero.png"))
print("wrote v6")