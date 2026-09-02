#!/usr/bin/env python3
"""M7 sim v2 — faithful PIL mirror of ui.cpp (v7 locked design).

ONE angle convention everywhere (PIL is y-down/clockwise like LGFX):
  12 o'clock = 270 deg, sweep increases clockwise.
Rings: full track + pct sweep + ROUNDED CAPS at both ends (matches firmware).
Timer ring: neutral fill from elapsed frac + comet head w/ fading tail.
Bleed check enforced (r<=146). Live data from companion on :8615."""
import json, math, os, time, urllib.request
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 466
CX = CY = 233
SAFE_R = 146

# ---- live data --------------------------------------------------------------
try:
    with urllib.request.urlopen("http://localhost:8615/api/summary", timeout=15) as r:
        D = json.load(r)
    c, a = D["cloud"], D["activity"]
    session_pct = c.get("session_pct") or 0.0
    weekly_pct = c.get("weekly_pct") or 0.0
    sess_min = c.get("session_reset_min", -1)
    week_min = c.get("weekly_reset_min", -1)
    elapsed = c.get("session_elapsed_frac") or 0.0
    today = a.get("today", {})
    req_min = today.get("req_per_min", 0.0)
    today_req, today_gen = today.get("requests", 0), today.get("generations", 0)
    LIVE = True
except Exception as e:
    print("companion unreachable (%s) — sample data" % e)
    session_pct, weekly_pct, sess_min, week_min = 2.8, 53.8, 185, 6905
    elapsed, req_min, today_req, today_gen = 0.39, 30.6, 293, 200
    LIVE = False

SESSION_WINDOW_S = 5 * 3600
if LIVE and c.get("session_reset_at"):
    try:
        t = time.mktime(time.strptime(c["session_reset_at"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        rem = max(0, t - time.time())
        f = 1.0 - rem / SESSION_WINDOW_S
        if 0 <= f <= 1:
            elapsed = f
    except Exception:
        pass

# ---- palette / fonts ---------------------------------------------------------
BG    = (9,11,17); INK=(240,242,248); DIM=(122,130,150); FAINT=(84,92,114)
TRACK = (30,34,48); CYAN=(86,208,226)
GREEN = (52,199,120); AMBER=(255,184,66); RED=(255,92,92)
NEUTRAL=(200,206,222); TFILL=(57,158,127)

def thresh(p): return GREEN if p < 70 else AMBER if p < 90 else RED
sess_col = thresh(session_pct)

def font(sz):
    try: return ImageFont.truetype("/System/Library/Fonts/Monaco.dfont", sz)
    except Exception:
        try: return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", sz)
        except Exception: return ImageFont.load_default()

viol = []
def mono(d, xy, s, sz, fill, anchor="mm"):
    d.text(xy, s, font=font(sz), fill=fill, anchor=anchor)
    bb = d.textbbox(xy, s, font=font(sz), anchor=anchor)
    for (x, y) in [(bb[0],bb[1]),(bb[2],bb[1]),(bb[0],bb[3]),(bb[2],bb[3])]:
        if math.hypot(x-CX, y-CY) > SAFE_R:
            viol.append((s[:20], int(math.hypot(x-CX, y-CY))))

# ---- arc helpers (unified convention) ---------------------------------------
def arc_deg(d, rO, rI, a0, a1, color):
    """PIL arc from a0 to a1 degrees (0=3 o'clock, clockwise, y-down)."""
    if a1 < a0: a0, a1 = a1, a0
    d.arc([CX-rO, CY-rO, CX+rO, CY+rO], a0, a1, fill=color, width=rO-rI)

def arc_wrapped(d, rO, rI, a0, a1, color):
    if a1 <= 360:
        arc_deg(d, rO, rI, a0, a1, color)
    else:
        arc_deg(d, rO, rI, a0, 360, color)
        arc_deg(d, rO, rI, 0, a1-360, color)

def cap(d, rO, rI, ang, color):
    """rounded end cap: disc of radius (rO-rI)/2 at band mid-radius"""
    rm, rc = (rO+rI)/2.0, (rO-rI)/2.0
    rad = math.radians(ang)
    x, y = CX + rm*math.cos(rad), CY + rm*math.sin(rad)
    d.ellipse([x-rc, y-rc, x+rc, y+rc], fill=color)

def draw_ring(d, rO, rI, pct, color):
    arc_deg(d, rO, rI, 0, 360, TRACK)
    if pct is None or pct <= 0.2:
        return
    pct = min(pct, 100)
    a0, a1 = 270, 270 + 3.6*pct
    arc_wrapped(d, rO, rI, a0, a1, color)
    cap(d, rO, rI, a0, color)                 # rounded start (12 o'clock)
    cap(d, rO, rI, a1, color)                 # rounded tip

def draw_timer(d, frac):
    rO, rI = 158, 152
    arc_deg(d, rO, rI, 0, 360, TRACK)
    f = max(0.005, min(frac, 1.0))
    a1 = 270 + 360*f
    arc_wrapped(d, rO, rI, 270, a1, TFILL)
    # comet: 3 fading tail segments behind the head + head dot
    head = a1
    for da0, da1, col in [(-26,-16,(60,66,88)), (-15,-6,DIM), (-5,0,NEUTRAL)]:
        s0, s1 = head+da0, head+da1
        if s0 < 0: s0 += 360
        if s1 < 0: s1 += 360
        if s0 > s1:
            arc_deg(d, rO+2, rI-2, s0, 360, col)
            arc_deg(d, rO+2, rI-2, 0, s1, col)
        else:
            arc_deg(d, rO+2, rI-2, s0, s1, col)
    cap(d, rO+2, rI-2, head, NEUTRAL)

# ---- face --------------------------------------------------------------------
im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)

draw_ring(d, 200, 188, weekly_pct, CYAN)
draw_ring(d, 180, 168, session_pct, sess_col)
draw_timer(d, elapsed)

# left: logo + activity
src = Image.open(os.path.join(HERE, "assets", "lobe-dark.png")).convert("RGBA")
a_ch = src.getchannel("A"); crop = a_ch.crop(a_ch.getbbox())
s = 104 / crop.height
logo = Image.new("RGBA", (int(crop.width*s), int(crop.height*s)), (0,0,0,0))
white = Image.new("RGBA", logo.size, (245,247,252,255))
logo.paste(white, (0,0), crop.resize(logo.size, Image.LANCZOS))
im.paste(logo, (CX-72-logo.width//2, CY-60-logo.height//2), logo)

mono(d, (CX-72, CY+26), f"{req_min:.1f}", 26, INK)
mono(d, (CX-72, CY+52), "req/min", 12, DIM)
mono(d, (CX-58, CY+76), f"{today_req} req {today_gen} gen", 11, FAINT)

# right: color-matched numbers
rx = CX + 14
def lt(x, y, s, sz, fill): mono(d, (x, y), s, sz, fill, anchor="lm")
lt(rx, CY-112, "SESSION", 12, DIM)
mono(d, (rx+60, CY-76), (f"{session_pct:.1f}" if session_pct < 10 else f"{session_pct:.0f}") + "%", 30, sess_col)
def cd(m):
    if m < 0: return "--"
    if m >= 1440: return f"{m//1440}d {m%1440//60}h"
    if m >= 60: return f"{m//60}h {m%60:02d}m"
    return f"{m}m"
lt(rx, CY-48, f"resets {cd(sess_min)}", 12, FAINT)
lt(rx, CY-16, "WEEKLY", 12, DIM)
mono(d, (rx+60, CY+22), (f"{weekly_pct:.1f}" if weekly_pct < 10 else f"{weekly_pct:.0f}") + "%", 30, CYAN)
lt(rx, CY+52, f"resets {cd(week_min)}", 12, FAINT)

print(f"bleed-check: {'PASS' if not viol else 'FAIL ' + str(viol)}")
print(f"LIVE={LIVE}  session={session_pct}% weekly={weekly_pct}% comet={elapsed:.2f}")
out = os.path.join(HERE, "sim", "sim-live.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
im.save(out)
print("wrote", out)