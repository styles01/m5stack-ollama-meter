#!/usr/bin/env python3
"""v3: iterate on A per James — logo smaller, center; rings outside; inner
circle SPLIT between logo and key stats. 3 micro-variants of that concept."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 466

src = Image.open(os.path.join(HERE, "assets", "lobe-dark.png")).convert("RGBA")
a = src.getchannel("A"); bbox = a.getbbox(); crop_a = a.crop(bbox)
lw, lh = crop_a.size
s = 96 / lh                      # SMALL logo (~96px tall)
logo = Image.new("RGBA", (int(lw*s), int(lh*s)), (0,0,0,0))
white = Image.new("RGBA", logo.size, (245,247,252,255))
mask = crop_a.resize(logo.size, Image.LANCZOS)
logo.paste(white, (0,0), mask)

def font(sz):
    try: return ImageFont.truetype("/System/Library/Fonts/Monaco.dfont", sz)
    except Exception: pass
    try: return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", sz)
    except Exception: return ImageFont.load_default()

BG    = (9,11,17); INK=(240,242,248); DIM=(122,130,150); FAINT=(74,82,104)
TRACK = (30,34,48); CLOUD=(112,138,255); CYAN=(86,208,226); GREEN=(52,199,120)
AMBER = (255,184,66); RED=(255,92,92); CARD=(22,26,38); DIV=(52,60,84)

D = dict(session=2.8, weekly=53.8, session_reset="3h 04m", reset="5d 03h",
         req=30.6, today=153, gen=110, err=6,
         hours=[1,0,0,0,0,0,0,0,2,4,9,14,11,18,22,16,25,31,28,44,61,88,121,153])

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED

def ring(d, cx, cy, rO, rI, pct, color, track=True):
    if track: d.arc([cx-rO, cy-rO, cx+rO, cy+rO], 0, 360, fill=TRACK, width=rO-rI)
    if pct and pct > 0.3:
        d.arc([cx-rO, cy-rO, cx+rO, cy+rO], -90, -90+3.6*min(pct,100), fill=color, width=rO-rI)

def comet(d, cx, cy, r, ang, color):
    d.arc([cx-r, cy-r, cx+r, cy+r], ang-30, ang, fill=INK, width=8)

def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)

def curved_bars(d, cx, cy, r0, vals, maxv):
    n=len(vals); span=110; step=span/(n-1)
    for i,v in enumerate(vals):
        ang = 90-span/2 + i*step
        h = 6 + (v/maxv)*40 if v else 3
        col = CYAN if i>=n-2 else (44,74,116)
        d.arc([cx-(r0+h), cy-(r0+h), cx+(r0+h), cy+(r0+h)], ang-1.7, ang+1.7, fill=col, width=6)

def logo_img():
    return logo

def paste_logo(im, cx, cy):
    im.paste(logo, (cx - logo.width // 2, cy - logo.height // 2), logo)

def base_face():
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    cx, cy = 233, 213
    ring(d, cx, cy, 196, 187, D["weekly"], CYAN)                     # weekly thin
    ring(d, cx, cy, 177, 147, D["session"], thresh(D["session"]))    # session fat
    comet(d, cx, cy, 161, 118, thresh(D["session"]))                 # comet on session ring
    mono(d, (cx, 42), "WEEKLY", 15, DIM)
    mono(d, (cx, 66), f"{D['weekly']:.0f}%", 24, CYAN)
    mono(d, (cx, 92), f"resets {D['reset']}", 13, FAINT)
    curved_bars(d, cx, cy, 96, D["hours"][-18:], max(D["hours"]))
    mono(d, (cx, 442), f"sync 12s", 14, FAINT)
    return im, d, cx, cy

def v_A1():
    """inner circle split HORIZONTALLY: logo top / stats bottom"""
    im, d, cx, cy = base_face()
    d.line([cx-92, cy+8, cx+92, cy+8], fill=DIV, width=2)            # split line
    im.paste(logo, (cx-logo.width//2, cy-92), logo)
    mono(d, (cx, cy+46), f"{D['session']:.1f}%", 42, INK)
    mono(d, (cx, cy+84), f"SESSION · resets {D['session_reset']}", 13, DIM)
    # compass: req/min left, today right
    mono(d, (52, cy+6), f"{D['req']:.1f}", 26, CYAN)
    mono(d, (52, cy+34), "req/min", 14, FAINT)
    mono(d, (414, cy+6), f"{D['today']}", 26, INK)
    mono(d, (414, cy+34), f"{D['gen']} gen", 14, FAINT)
    return im

def v_A2():
    """inner circle split VERTICALLY: logo left / session% right"""
    im, d, cx, cy = base_face()
    d.line([cx, cy-96, cx, cy+104], fill=DIV, width=2)
    paste_logo(im, cx-64, cy-4)
    mono(d, (cx+66, cy-38), f"{D['session']:.1f}%", 32, INK)
    mono(d, (cx+66, cy-6), "SESSION", 13, DIM)
    mono(d, (cx+66, cy+22), f"resets {D['session_reset']}", 12, FAINT)
    mono(d, (cx+66, cy+36), f"{D['req']:.0f} rpm", 15, CYAN)
    mono(d, (414, cy+6), f"{D['today']}", 26, INK)
    mono(d, (414, cy+34), f"{D['gen']} gen", 14, FAINT)
    mono(d, (52, cy+6), f"{D['req']:.1f}", 26, CYAN)
    mono(d, (52, cy+34), "req/min", 14, FAINT)
    return im

def v_A3():
    """inner circle stacked tight: logo, big %, session+reset, req/min"""
    im, d, cx, cy = base_face()
    im.paste(logo, (cx-logo.width//2, cy-102), logo)
    mono(d, (cx, cy+2), f"{D['session']:.1f}%", 40, INK)
    mono(d, (cx, cy+36), f"SESSION · resets {D['session_reset']}", 13, DIM)
    mono(d, (cx, cy+66), f"{D['req']:.0f} req/min", 15, CYAN)
    mono(d, (414, cy+6), f"{D['today']}", 24, INK)
    mono(d, (414, cy+32), f"{D['gen']} gen · {D['err']} err", 13, FAINT)
    mono(d, (52, cy+6), "WEEK", 13, FAINT)
    mono(d, (52, cy+30), f"{D['weekly']:.0f}%", 22, CYAN)
    mono(d, (52, cy+56), f"resets {D['reset']}", 12, FAINT)
    return im

tiles = [("A1 · SPLIT H", v_A1), ("A2 · SPLIT V", v_A2), ("A3 · STACKED", v_A3)]
sheet = Image.new("RGB", (W*3+120, H+130), (15,17,25)); sd = ImageDraw.Draw(sheet)
try: lab = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
except Exception: lab = font(36)
for i,(name,fn) in enumerate(tiles):
    x,y = 30+i*(W+30), 54
    sd.text((x,y-44), name, font=lab, fill=INK)
    sheet.paste(fn(), (x,y))
    sd.rectangle([x-1,y-1,x+W,y+H], outline=(70,78,100), width=1)
sheet.save(os.path.join(HERE, "ui-contact-sheet-v3.png"))
for n,fn in tiles: fn().save(os.path.join(HERE, f"tile-v3-{n[0].lower()}{n[1]}.png"))
print("wrote v3 sheet")