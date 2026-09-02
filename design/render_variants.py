#!/usr/bin/env python3
"""Render 4 labeled UI design variants for the M5Stack StopWatch Ollama meter
(round 466x466 AMOLED) as a contact sheet. Uses live-ish sample data from the
companion service's real output. PIL only, no network."""
import math, os
from PIL import Image, ImageDraw, ImageFont

W = H = 466
OUT = os.path.dirname(os.path.abspath(__file__))

# --- sample data (from live companion pull 2026-09-01) ---
D = dict(session_pct=2.8, weekly_pct=53.8, reset_in="3h 04m", sync_age="12s ago",
         model="nomic-embed-text", vram_mb=370, unload_in="0:18", installed=20,
         req_min=30.6, today_req=153, today_gen=110, today_err=6,
         hours=[1,0,0,0,0,0,0,0,2,4,9,14,11,18,22,16,25,31,28,44,61,88,121,153])

def font(sz, mono=False):
    paths = (["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.dfont"]
             if mono else ["/System/Library/Fonts/Helvetica.ttc",
                           "/System/Library/Fonts/HelveticaNeue.ttc"])
    for p in paths:
        try: return ImageFont.truetype(p, sz)
        except Exception: continue
    return ImageFont.load_default()

BG      = (10, 12, 18)
CARD    = (22, 26, 38)
INK     = (238, 240, 246)
DIM     = (120, 128, 148)
GREEN   = (52, 199, 120)
AMBER   = (255, 184, 66)
RED     = (255, 92, 92)
OLLAMA  = (112, 138, 255)   # ollama-ish indigo
CYAN    = (86, 208, 226)

def ring(draw, cx, cy, r, pct, width, color, track=(38, 42, 56)):
    draw.arc([cx-r, cy-r, cx+r, cy+r], 0, 360, fill=track, width=width)
    if pct > 0.5:
        draw.arc([cx-r, cy-r, cx+r, cy+r], -90, -90 + 3.6*min(pct,100), fill=color, width=width)

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED

def tile_A():  # BIG RINGS — one hero ring, one inner
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    ring(d, 233, 205, 150, D["session_pct"], 26, OLLAMA)
    ring(d, 233, 205, 108, D["weekly_pct"], 16, CYAN)
    f = font(92)
    t = f"{D['session_pct']:.0f}%"
    bb = d.textbbox((0,0), t, font=f)
    d.text((233-(bb[2]-bb[0])/2, 205-(bb[3]-bb[1])/2 - 34), t, font=f, fill=INK)
    f2 = font(26, mono=True); s = f"session"
    bb = d.textbbox((0,0), s, font=f2)
    d.text((233-(bb[2]-bb[0])/2, 205+18), s, font=f2, fill=DIM)
    d.text((36, 392), f"WEEKLY {D['weekly_pct']:.1f}%", font=font(30), fill=CYAN)
    d.text((36, 428), f"reset {D['reset_in']}  ·  sync {D['sync_age']}", font=font(24, mono=True), fill=DIM)
    d.text((356, 28), "OLLAMA CLOUD", font=font(20, mono=True), fill=OLLAMA)
    return im

def tile_B():  # SPLIT — top cloud gauges, bottom activity bars
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.text((40, 30), "CLOUD", font=font(24, mono=True), fill=OLLAMA)
    ring(d, 120, 150, 72, D["session_pct"], 18, OLLAMA)
    d.text((86, 134), f"{D['session_pct']:.0f}%", font=font(38), fill=INK)
    d.text((76, 196), "session", font=font(20, mono=True), fill=DIM)
    ring(d, 300, 150, 72, D["weekly_pct"], 18, CYAN)
    d.text((266, 134), f"{D['weekly_pct']:.0f}%", font=font(38), fill=INK)
    d.text((266, 196), "weekly", font=font(20, mono=True), fill=DIM)
    d.line([40, 244, 426, 244], fill=(40, 46, 62), width=2)
    d.text((40, 260), f"ACTIVITY  {D['req_min']:.1f}/min", font=font(24, mono=True), fill=CYAN)
    bw, gap, x0, base, mh = 13, 3.4, 40, 420, 110
    hm = max(max(D["hours"]), 1)
    for i, v in enumerate(D["hours"][-24:]):
        h = int(mh and v / hm * mh)
        c = CYAN if i >= 22 else (52, 96, 140)
        d.rounded_rectangle([x0 + i*(bw+gap), base-h, x0 + i*(bw+gap)+bw, base], 3, fill=c)
    d.text((40, 428), f"today {D['today_req']} req · {D['today_gen']} gen · {D['today_err']} err",
           font=font(20, mono=True), fill=DIM)
    return im

def tile_C():  # BIG NUMBER — giant %, thin arc, ultra minimal
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    ring(d, 233, 233, 190, D["weekly_pct"], 10, (46, 52, 72))
    ring(d, 233, 233, 172, D["weekly_pct"], 10, thresh(D["weekly_pct"]))
    f = font(170)
    t = f"{D['session_pct']:.1f}%"
    bb = d.textbbox((0,0), t, font=f)
    d.text((233-(bb[2]-bb[0])/2, 233-(bb[3]-bb[1])/2 - 44), t, font=f, fill=INK)
    d.text((233, 214), "SESSION USAGE", font=font(26, mono=True), fill=DIM, anchor="mm")
    d.text((233, 246), f"weekly {D['weekly_pct']:.0f}%  ·  resets {D['reset_in']}",
           font=font(22, mono=True), fill=(90, 98, 118), anchor="mm")
    d.text((233, 440), f"local {D['req_min']:.0f} req/min", font=font(22, mono=True), fill=CYAN, anchor="mm")
    return im

def tile_D():  # DASHBOARD — everything at once, dense
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    ring(d, 108, 128, 66, D["session_pct"], 14, OLLAMA)
    d.text((78, 114), f"{D['session_pct']:.0f}%", font=font(30), fill=INK)
    d.text((48, 168), "session", font=font(17, mono=True), fill=DIM)
    ring(d, 268, 128, 66, D["weekly_pct"], 12, thresh(D["weekly_pct"]))
    d.text((242, 116), f"{D['weekly_pct']:.0f}%", font=font(26), fill=INK)
    d.text((222, 166), "weekly", font=font(17, mono=True), fill=DIM)
    d.text((368, 116), f"{D['req_min']:.0f}", font=font(40), fill=CYAN)
    d.text((356, 164), "req/min", font=font(17, mono=True), fill=DIM)
    d.line([36, 208, 430, 208], fill=(40, 46, 62), width=2)
    d.text((36, 220), "LOCAL · ollama on mac", font=font(19, mono=True), fill=DIM)
    d.rounded_rectangle([36, 250, 430, 316], 10, fill=CARD)
    d.text((52, 262), D["model"], font=font(24, mono=True), fill=INK)
    d.rounded_rectangle([52, 292, 414, 302], 5, fill=(40, 46, 62))
    d.rounded_rectangle([52, 292, 52+int(362*0.18), 302], 5, fill=OLLAMA)
    d.text((52, 306), f"{D['vram_mb']} MB VRAM", font=font(16, mono=True), fill=DIM)
    d.text((300, 306), f"unload {D['unload_in']}  ·  {D['installed']} models", font=font(16, mono=True), fill=DIM)
    bw, gap, x0, base, mh = 11, 2.6, 40, 430, 90
    hm = max(max(D["hours"]), 1)
    for i, v in enumerate(D["hours"][-24:]):
        h = int(v / hm * mh)
        d.rounded_rectangle([x0+i*(bw+gap), base-h, x0+i*(bw+gap)+bw, base], 2,
                            fill=(52, 96, 140) if i < 22 else CYAN)
    return im

tiles = [("A · RINGS", tile_A), ("B · SPLIT", tile_B), ("C · BIG NUMBER", tile_C), ("D · DASHBOARD", tile_D)]
sheet = Image.new("RGB", (W*2+90, H*2+130), (16, 18, 26))
sd = ImageDraw.Draw(sheet)
lab = font(40)
for i, (name, fn) in enumerate(tiles):
    im = fn()
    x, y = 30 + (i % 2)*(W+30), 50 + (i // 2)*(H+80)
    sd.text((x, y-44), name, font=lab, fill=INK)
    sheet.paste(im, (x, y))
    sd.rectangle([x-1, y-1, x+W, y+H], outline=(70, 78, 100), width=1)
sheet.save(os.path.join(OUT, "ui-contact-sheet.png"))
for name, fn in tiles:
    fn().save(os.path.join(OUT, f"tile-{name[0].lower()}.png"))
print("wrote contact sheet + 4 tiles to", OUT)