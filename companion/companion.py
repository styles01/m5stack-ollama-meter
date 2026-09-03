#!/usr/bin/env python3
"""
ollama-meter-companion — Mac-side brain for the M5Stack Ollama Usage Meter.

Serves GET /api/summary on :8615 with:
  cloud    — ollama.com web-dashboard usage (session %, weekly %, reset times)
             source: OpenClaw cron JSON if fresh, else direct fetch with saved cookies
  local    — local Ollama server state (/api/ps loaded models + VRAM + unload countdown, /api/tags count)
  activity — request activity derived from ~/.ollama/logs/server.log GIN lines
             (today totals, trailing 5-min req/min, 24h hourly buckets, persisted)

stdlib-only. Read-only wrt OpenClaw and Ollama data. State file lives next to this script.
"""

import json
import os
import re
import subprocess  # nosec - only used for scutil-free local ip lookup via socket
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- paths -----------------------------------------------------------------
# Defaults suit the reference setup; override via env vars for other installs.
HOME = os.path.expanduser("~")
CC_DATA = os.environ.get(
    "METER_CC_DATA", os.path.join(HOME, ".openclaw/workspace/command-center/data"))
USAGE_JSON = os.environ.get("METER_USAGE_JSON", os.path.join(CC_DATA, "ollama-usage.json"))
COOKIES_JSON = os.environ.get(
    "METER_COOKIES_JSON", os.path.join(CC_DATA, "ollama-cookies.json"))
OLLAMA_LOG = os.environ.get("METER_OLLAMA_LOG", os.path.join(HOME, ".ollama/logs/server.log"))
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

PORT = 8615
SESSION_WINDOW_S = 5 * 3600       # ollama.com session window ≈5h (rolling)
CLOUD_STALE_S = 2 * 3600          # cron JSON older than this -> try direct cookie fetch
CLOUD_DIRECT_REFRESH_S = 120      # re-scrape ollama.com at most every 2 min
CLOUD_HARD_STALE_S = 24 * 3600    # older than this -> mark stale to the device
OLLAMA_BASE = "http://localhost:11434"
HTTP_TIMEOUT = 4

GIN_RE = re.compile(
    r"\[GIN\]\s+(\d{4}/\d{2}/\d{2}) - (\d{2}:\d{2}:\d{2})\s*\|\s*(\d{3})\s*\|\s*"
    r"([0-9hmsµn.]+)\s*\|\s*([0-9a-fA-F:.]+)\s*\|\s*(\w+)\s+\"([^\"]+)\""
)
GEN_PATHS = ("/api/chat", "/api/generate", "/v1/chat/completions", "/v1/completions")

# --- state (guarded by LOCK) ----------------------------------------------
LOCK = threading.Lock()
STATE = {
    "buckets": {},        # "YYYY-MM-DDTHH" (local) -> request count
    "log_offset": None,   # byte offset into server.log
    "log_inode": None,
    "today": {},          # today's totals: {"requests": n, "generations": n, "errors": n, "by_endpoint": {...}}
    "req_rate": 0.0,      # generations+requests per min over trailing 5 min window (requests)
    "recent": [],         # trailing ring of (epoch, is_gen) for rate calc
    "last_cloud_fetch": 0.0,
    "cloud_direct": None, # last direct-fetch result dict or None
}


def _now_local():
    t = time.localtime()
    return t


def _hour_key(epoch=None):
    return time.strftime("%Y-%m-%dT%H", time.localtime(epoch if epoch is not None else time.time()))


def _today_key():
    return time.strftime("%Y-%m-%d")


# ---------------------------------------------------------------- cloud ----
def load_cloud(max_age_ok_s):
    """Prefer OpenClaw cron JSON if fresh. Return (data, source)."""
    try:
        st = os.stat(USAGE_JSON)
        age = time.time() - st.st_mtime
        with open(USAGE_JSON) as f:
            data = json.load(f)
        if data.get("available") and age <= max_age_ok_s:
            data["_source"] = "openclaw-cron"
            data["_age_s"] = int(age)
            return data, "cron"
        data["_source"] = "openclaw-cron-stale"
        data["_age_s"] = int(age)
        return data, "stale"
    except Exception as e:
        return {"available": False, "error": f"no cron data: {e}", "_source": "none", "_age_s": None}, "none"


def cookie_header():
    try:
        with open(COOKIES_JSON) as f:
            cookies = json.load(f)
    except Exception:
        return None
    if isinstance(cookies, dict) and "cookies" in cookies:
        cookies = cookies["cookies"]
    parts = []
    try:
        for c in cookies:
            name = c.get("name")
            val = c.get("value")
            if name and val:
                parts.append(f"{name}={val}")
    except AttributeError:
        return None
    return "; ".join(parts) if parts else None


def fetch_usage_api():
    """Official path: GET https://ollama.com/api/usage with
    'Authorization: Bearer $OLLAMA_API_KEY' (API key from
    ollama.com/settings/keys). Returns the same flat shape as
    fetch_cloud_direct so downstream code is agnostic. No reset timestamps in
    the response — computed from the globally-aligned 5h/7d windows."""
    key = os.environ.get("OLLAMA_API_KEY")
    if not key:
        try:
            with open(os.path.join(CC_DATA, "ollama-api-key.txt")) as f:
                key = f.read().strip()
        except Exception:
            return None
    req = urllib.request.Request(
        "https://ollama.com/api/usage",
        headers={"Authorization": f"Bearer {key}",
                 "User-Agent": "ollama-meter-companion/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None
    limits = d.get("limits") or {}
    sess = limits.get("session") or {}
    week = limits.get("weekly") or {}
    now = time.time()
    out = {
        "available": True,
        "session_pct": round(sess["usage"] * 100, 1) if "usage" in sess else None,
        "weekly_pct": round(week["usage"] * 100, 1) if "usage" in week else None,
        "session_reset_at": _aligned_reset_iso(now, SESSION_WINDOW_S),
        "weekly_reset_at": _aligned_reset_iso(now, 7 * 24 * 3600),
        "_source": "usage-api",
        "lastUpdated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    models = sess.get("models") or []
    if models:
        top = max(models, key=lambda m: m.get("request_count", 0))
        out["top_models"] = [(top.get("name"), top.get("request_count", 0))]
    return out


def fetch_cloud_direct():
    """Direct HTTPS GET of ollama.com/settings using saved cookies. Parses the
    server-rendered usage numbers, reset timestamps and per-model requests.
    Kept best-effort: any failure -> None."""
    ck = cookie_header()
    if not ck:
        return None
    url = "https://ollama.com/settings"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ollama-meter-companion/1.0",
        "Cookie": ck,
        "Accept": "text/html",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:
        return None
    out = {}
    m = re.search(r"Session usage.*?(\d+(?:\.\d+)?)\s*%", html, re.S)
    if m:
        out["session_pct"] = float(m.group(1))
    m = re.search(r"Weekly usage.*?(\d+(?:\.\d+)?)\s*%", html, re.S)
    if m:
        out["weekly_pct"] = float(m.group(1))
    # reset timestamps: each usage block = label -> bar -> "Resets ..." div.
    # Split at the Weekly label; find data-time within each section.
    sess_pos = html.find("Session usage")
    week_pos = html.find("Weekly usage")
    if sess_pos != -1 and week_pos != -1 and week_pos > sess_pos:
        m = re.search(r'data-time="([^"]+)"', html[sess_pos:week_pos])
        if m:
            out["session_reset_at"] = m.group(1)
        m = re.search(r'data-time="([^"]+)"', html[week_pos:])
        if m:
            out["weekly_reset_at"] = m.group(1)
    # per-model requests (top by requests, from usage-bar segments)
    models = re.findall(r'data-model="([^"]+)"\s+data-requests="(\d+)"', html)
    if models:
        seen = {}
        for name, reqs in models:
            seen[name] = max(seen.get(name, 0), int(reqs))
        out["top_models"] = sorted(seen.items(), key=lambda kv: -kv[1])[:3]
    out["available"] = bool(out.get("session_pct") is not None or out.get("weekly_pct") is not None)
    out["_source"] = "direct-cookie"
    out["lastUpdated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return out if out.get("available") else None


def _iso_to_epoch(iso):
    """Parse '2026-09-03T04:00:00Z' as UTC and return a true epoch.
    calendar.timegm treats the struct as UTC (unlike mktime, which applies
    the local zone) — this is the correct conversion."""
    import calendar
    t = time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
    return calendar.timegm(t)


def _aligned_reset_iso(now_epoch, window_s):
    """Next boundary of a globally-aligned window (5h session / 7d weekly)."""
    nxt = (now_epoch // window_s + 1) * window_s
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(nxt))


def normalize_cloud(cron_data, direct_data):
    """Merge cron JSON + direct-fetch into one flat shape for the device."""
    out = {
        "available": False,
        "session_pct": None,
        "weekly_pct": None,
        "session_reset_at": None,
        "weekly_reset_at": None,
        "session_elapsed_frac": None,
        "top_models": [],
        "updated_at": None,
        "age_s": None,
        "source": "none",
    }
    if cron_data:
        su = cron_data.get("sessionUsage") or {}
        wu = cron_data.get("weeklyUsage") or {}
        out["available"] = bool(cron_data.get("available"))
        out["session_pct"] = su.get("percentage")
        out["weekly_pct"] = wu.get("percentage")
        out["session_reset_at"] = su.get("resetAt")
        out["weekly_reset_at"] = wu.get("resetAt")
        out["updated_at"] = cron_data.get("lastUpdated")
        out["age_s"] = cron_data.get("_age_s")
        out["source"] = cron_data.get("_source", "none")
    if direct_data:
        out["available"] = True
        if direct_data.get("session_pct") is not None:
            out["session_pct"] = direct_data["session_pct"]
        if direct_data.get("weekly_pct") is not None:
            out["weekly_pct"] = direct_data["weekly_pct"]
        if direct_data.get("session_reset_at"):
            out["session_reset_at"] = direct_data["session_reset_at"]
        if direct_data.get("weekly_reset_at"):
            out["weekly_reset_at"] = direct_data["weekly_reset_at"]
        if direct_data.get("top_models"):
            out["top_models"] = direct_data["top_models"]
            out["top_model"] = direct_data["top_models"][0][0]
            out["top_model_req"] = direct_data["top_models"][0][1]
        out["age_s"] = 0
        # label honestly: usage-api result vs cookie scrape
        out["source"] = direct_data.get("_source", "direct-cookie")
    # comet data: fraction of the session window elapsed (window=5h default;
    # ollama resets are rolling, so remaining <= window)
    if out.get("session_reset_at"):
        try:
            t = _iso_to_epoch(out["session_reset_at"])
            remaining = max(0.0, t - time.time())
            win = SESSION_WINDOW_S
            out["session_elapsed_frac"] = round(max(0.0, min(1.0, 1.0 - remaining / win)), 3)
            out["session_reset_min"] = int(remaining // 60)
        except Exception:
            pass
    if out.get("weekly_reset_at"):
        try:
            t = _iso_to_epoch(out["weekly_reset_at"])
            out["weekly_reset_min"] = int(max(0.0, t - time.time()) // 60)
        except Exception:
            pass
    return out


def cloud_payload():
    with LOCK:
        direct = STATE.get("cloud_direct")
        last_fetch = STATE.get("last_cloud_fetch", 0)
    # PRIORITY 1: official usage API with an API key (no cookies needed).
    # Not throttled — cheap authenticated JSON, and the rolling-window guard
    # below keeps reset times honest.
    api = fetch_usage_api()
    if api:
        return normalize_cloud(None, api)
    # PRIORITY 2/3: cookie scrape (direct) or stale cron JSON
    data, kind = load_cloud(CLOUD_STALE_S)
    # refresh direct fetch at most every CLOUD_DIRECT_REFRESH_S
    if (kind == "stale" or kind == "none") and time.time() - last_fetch > CLOUD_DIRECT_REFRESH_S:
        d = fetch_cloud_direct()
        with LOCK:
            STATE["last_cloud_fetch"] = time.time()
            if d:
                STATE["cloud_direct"] = d
            else:
                # cookie expired / fetch failing: DROP the cached direct result
                # so the device shows degraded '--' instead of frozen percentages
                STATE["cloud_direct"] = None
        if d:
            direct = d
    # rolling window guard: if the cached session reset is already in the past,
    # the window has rolled since we scraped -> cached numbers are WRONG.
    # Drop them and force a fresh scrape right now (don't show a lie).
    if direct and direct.get("session_reset_at"):
        try:
            t = _iso_to_epoch(direct["session_reset_at"])
            if t - time.time() <= 0:
                d2 = fetch_cloud_direct()
                with LOCK:
                    STATE["last_cloud_fetch"] = time.time()
                    STATE["cloud_direct"] = d2
                if d2:
                    direct = d2
                else:
                    direct = None
        except Exception:
            pass
    return normalize_cloud(data, direct)


# ---------------------------------------------------------------- local ----
def _get_json(url, timeout=HTTP_TIMEOUT):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def local_payload():
    ps = _get_json(OLLAMA_BASE + "/api/ps")
    tags = _get_json(OLLAMA_BASE + "/api/tags")
    now = time.time()
    models = []
    if ps:
        for m in ps.get("models", []):
            exp = m.get("expires_at")
            countdown = None
            if exp:
                try:
                    t = time.mktime(time.strptime(exp[:19], "%Y-%m-%dT%H:%M:%S"))
                    countdown = max(0, int(t - now))
                except Exception:
                    pass
            models.append({
                "name": m.get("name"),
                "size_vram": m.get("size_vram"),
                "size": m.get("size"),
                "context_length": m.get("context_length"),
                "quant": (m.get("details") or {}).get("quantization_level"),
                "unload_in_s": countdown,
            })
    return {
        "server_ok": ps is not None,
        "version": (_get_json(OLLAMA_BASE + "/api/version") or {}).get("version"),
        "loaded": models,
        "models_installed": len((tags or {}).get("models", [])),
        "checked_at": int(now),
    }


# ------------------------------------------------------------- activity ----
def _file_identity(path):
    st = os.stat(path)
    return st.st_ino, st.st_size


def parse_new_lines(text):
    """Feed new GIN lines into buckets/counters. Returns n_lines_parsed."""
    today = _today_key()
    n = 0
    with LOCK:
        for line in text.splitlines():
            m = GIN_RE.search(line)
            if not m:
                continue
            n += 1
            gdate, _gtime, status, _dur, _ip, method, path = m.groups()
            gdate = gdate.replace("/", "-")  # "2026/09/01" -> "2026-09-01"
            if gdate != today:
                continue
            path_q = path.split("?")[0]
            is_gen = method == "POST" and any(path_q.startswith(p) for p in GEN_PATHS)
            epoch = time.time()
            hk = _hour_key(epoch)
            STATE["buckets"][hk] = STATE["buckets"].get(hk, 0) + 1
            t = STATE["today"]
            t["requests"] = t.get("requests", 0) + 1
            if is_gen:
                t["generations"] = t.get("generations", 0) + 1
            ep = t.setdefault("by_endpoint", {})
            key = f"{method} {path_q}"
            ep[key] = ep.get(key, 0) + 1
            try:
                if int(status) >= 400:
                    t["errors"] = t.get("errors", 0) + 1
            except ValueError:
                pass
            STATE["recent"].append((epoch, 1))
            # prune ring
            cutoff = epoch - 3600
            if len(STATE["recent"]) > 4000:
                STATE["recent"] = [r for r in STATE["recent"] if r[0] > cutoff][-2000:]
        # prune buckets > 48h
        cutoff_hk = _hour_key(time.time() - 48 * 3600)
        STATE["buckets"] = {k: v for k, v in STATE["buckets"].items() if k >= cutoff_hk}
        # rate: trailing 5 min
        cutoff = time.time() - 300
        rate_n = sum(1 for e, _ in STATE["recent"] if e > cutoff)
        STATE["req_rate"] = round(rate_n / 5.0, 2)
        if STATE["today"].get("requests"):
            STATE["today"]["req_per_min"] = STATE["req_rate"]
    return n


def activity_tail():
    """Incrementally tail the Ollama server log; update counters. Cheap (<64KB)."""
    try:
        ino, size = _file_identity(OLLAMA_LOG)
    except FileNotFoundError:
        return
    with LOCK:
        offset = STATE["log_offset"]
        cur_ino = STATE["log_inode"]
    if offset is None or cur_ino != ino or offset > size:
        start = max(0, size - 65536)
        offset = start
        if start:
            with open(OLLAMA_LOG, "rb") as f:
                f.seek(start)
                f.readline()  # discard partial line
                offset = start + f.tell() - len(b"")
                offset = f.tell()
    try:
        with open(OLLAMA_LOG, "rb") as f:
            f.seek(offset)
            chunk = f.read(262144)
    except Exception:
        return
    if chunk:
        # keep only complete lines
        last_nl = chunk.rfind(b"\n")
        if last_nl == -1:
            return
        complete = chunk[: last_nl + 1]
        new_off = offset + last_nl + 1
        parse_new_lines(complete.decode("utf-8", "replace"))
        with LOCK:
            STATE["log_offset"] = new_off
            STATE["log_inode"] = ino
    else:
        with LOCK:
            STATE["log_offset"] = offset
            STATE["log_inode"] = ino


def activity_payload():
    with LOCK:
        today = dict(STATE["today"])
        buckets = dict(STATE["buckets"])
        by_ep = today.pop("by_endpoint", {})
    hours = [{"hour": k[11:13] + ":00", "count": v} for k, v in sorted(buckets.items()) if k.startswith(_today_key())]
    return {
        "today": today,
        "by_endpoint_top": sorted(by_ep.items(), key=lambda kv: -kv[1])[:6],
        "hourly_today": hours,
    }


# -------------------------------------------------------------- summary ----
def summary():
    return {
        "cloud": cloud_payload(),
        "local": local_payload(),
        "activity": activity_payload(),
        "generated_at": int(time.time()),
        "device_hint": {"host": socket_lan_ip(), "port": PORT},
    }


def socket_lan_ip():
    try:
        s = None
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except Exception:
        return "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass


# ------------------------------------------------------------- background --
def bg_tail_loop():
    while True:
        try:
            activity_tail()
        except Exception:
            pass
        time.sleep(2)


def save_state():
    with LOCK:
        snap = {"buckets": STATE["buckets"], "log_offset": STATE["log_offset"], "log_inode": STATE["log_inode"]}
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(snap, f)
    except Exception:
        pass


def load_state():
    try:
        with open(STATE_FILE) as f:
            snap = json.load(f)
        with LOCK:
            STATE["buckets"] = snap.get("buckets", {})
            STATE["log_offset"] = snap.get("log_offset")
            STATE["log_inode"] = snap.get("log_inode")
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")   # portal page cross-origin
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/summary":
            payload = summary()
        elif path == "/api/health":
            payload = {"ok": True, "ts": int(time.time())}
        elif path == "/api/host-info":
            payload = {"ip": socket_lan_ip(), "port": PORT, "name": "ollama-meter"}
        else:
            payload = {"error": "not found"}
        code = 200 if path != "/x" else 404
        if path not in ("/api/summary", "/api/health", "/api/host-info"):
            code = 404
        body = json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quiet


def start_mdns_advertise():
    """Register service instance 'ollama-meter' under standard _http._tcp via
    macOS dns-sd (system binary) — matches the device's MDNS.queryService
    lookup. Also gives the portal page a resolvable ollama-meter.local
    hostname via the SRV record. Subprocess lives as long as we do."""
    try:
        subprocess.Popen(
            ["/usr/bin/dns-sd", "-R", "ollama-meter", "_http._tcp", ".", str(PORT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("advertising ollama-meter._http._tcp (mDNS)", flush=True)
    except Exception as e:
        print("mDNS advertise failed (non-fatal):", e, flush=True)


def bg_beacon_loop():
    """UDP broadcast beacon: 'OLLAMA-METER <ip> <port>' every 3s on :8616.
    Devices that can't use mDNS (mesh AP isolation) learn our IP from this."""
    import socket as _s
    sock = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
    sock.setsockopt(_s.SOL_SOCKET, _s.SO_BROADCAST, 1)
    ip = socket_lan_ip()
    subnet_bc = ".".join(ip.split(".")[:3]) + ".255"
    payload = f"OLLAMA-METER {ip} {PORT}".encode()
    while True:
        for dst in (subnet_bc, "255.255.255.255"):
            try:
                sock.sendto(payload, (dst, 8616))
            except Exception:
                pass
        time.sleep(3)


def main():
    load_state()
    start_mdns_advertise()
    threading.Thread(target=bg_tail_loop, daemon=True).start()
    threading.Thread(target=bg_beacon_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"ollama-meter-companion listening on 0.0.0.0:{PORT} (LAN ip: {socket_lan_ip()})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        save_state()


if __name__ == "__main__":
    main()