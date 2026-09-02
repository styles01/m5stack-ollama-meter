#!/usr/bin/env python3
"""Analyze ollama-settings.har: inventory, auth, data contract, HTML fallback, recommendation.
Never prints cookie/token VALUES — names and structure only."""
import json, re, sys
from urllib.parse import urlparse
from collections import OrderedDict

HAR = "/Users/clawdio/.openclaw/workspace/ollama-settings.har"

with open(HAR, "r", encoding="utf-8", errors="replace") as f:
    har = json.load(f)

entries = har.get("log", {}).get("entries", [])
print(f"# total entries: {len(entries)}")
print(f"# har creator: {json.dumps(har['log'].get('creator', {}))}")

# ---------- 1. INVENTORY ----------
inventory = []  # dicts
domains = OrderedDict()
for i, e in enumerate(entries):
    req = e.get("request", {})
    res = e.get("response", {})
    url = req.get("url", "")
    method = req.get("method", "")
    status = res.get("status", 0)
    mime = (res.get("content", {}) or {}).get("mimeType", "")
    size = (res.get("content", {}) or {}).get("size", 0)
    body = (res.get("content", {}) or {}).get("text", None)
    domain = urlparse(url).netloc or "?"
    path = urlparse(url).path or "/"
    entry = {
        "idx": i,
        "method": method,
        "url": url,
        "domain": domain,
        "path": path,
        "status": status,
        "mime": mime,
        "size": size,
        "has_body": bool(body),
        "body_len": len(body) if body else 0,
    }
    inventory.append(entry)
    domains.setdefault(domain, []).append(entry)

print("\n== INVENTORY (by domain) ==")
for d, es in domains.items():
    print(f"\n## {d}  ({len(es)} entries)")
    for e in es:
        print(f"  [{e['idx']:>3}] {e['method']:>4} {e['status'] or '---':>3} {e['mime'][:40]:<40} size={e['size']:>8} len={e['body_len']:>8} {e['url'][:130]}")

# ---------- 2. AUTH: headers for key requests ----------
print("\n== AUTH (request headers by NAME, values redacted) ==")
interesting = [e for e in inventory if "ollama" in e["domain"] and (e["path"].startswith("/settings") or e["path"].startswith("/api"))]
if not interesting:
    interesting = [e for e in inventory if e["method"] == "GET" and "ollama" in e["domain"]][:5]

auth_report = []
for e in interesting:
    ent = entries[e["idx"]]
    req = ent["request"]
    hdrs = [h["name"] for h in req.get("headers", [])]
    cookies_hdr = req.get("cookies", []) or []
    cookie_names = []
    for h in req.get("headers", []):
        if h["name"].lower() == "cookie" and h.get("value"):
            # parse names only from the raw Cookie header
            cookie_names += [c.split("=", 1)[0].strip() for c in h["value"].split(";") if c.strip()]
    # dedupe preserving order
    seen = set(); cookie_names = [c for c in cookie_names if not (c in seen or seen.add(c))]
    print(f"\n[{e['idx']}] {e['method']} {e['url'][:120]} -> {e['status']}")
    print(f"  header names: {hdrs}")
    print(f"  cookie names (from Cookie header): {cookie_names}")
    print(f"  HAR cookies array: {[c.get('name') for c in cookies_hdr]}")
    print(f"  auth header present: {[h for h in hdrs if h.lower() in ('authorization','x-csrf-token','x-xsrf-token','x-requested-with','x-api-key')]}")
    auth_report.append({"idx": e["idx"], "url": e["url"], "headers": hdrs, "cookie_names": cookie_names})

# Check Set-Cookie response headers for key requests (names only)
print("\n== SET-COOKIE (names only) ==")
for e in interesting:
    ent = entries[e["idx"]]
    for h in ent["response"].get("headers", []):
        if h["name"].lower() == "set-cookie":
            name = h["value"].split("=", 1)[0]
            print(f"  [{e['idx']}] {e['url'][:80]} Set-Cookie: {name}")

# ---------- 3. DATA CONTRACT: JSON API responses ----------
print("\n== JSON RESPONSES ==")
json_entries = [e for e in inventory if e["has_body"] and (
    "json" in e["mime"].lower() or (e["body_len"] > 0 and e["body_len"] < 200000 and entries[e["idx"]]["response"]["content"].get("text","").lstrip()[:1] in "{["))]
print(f"# json-ish entries: {[e['idx'] for e in json_entries]}")

def schema_of(obj, depth=0, path=""):
    """Return compact schema: {path}: type"""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if isinstance(v, (dict, list)):
                out.append(f"{p}: {type(v).__name__}")
                if depth < 8:
                    out += schema_of(v, depth + 1, p)
            else:
                out.append(f"{p}: {type(v).__name__} = <redacted>")
    elif isinstance(obj, list):
        if obj:
            out.append(f"{path}[] (len={len(obj)}): sample element schema")
            if depth < 8:
                out += schema_of(obj[0], depth + 1, f"{path}[0]")
        else:
            out.append(f"{path}: list(empty)")
    return out

json_schemas = {}
for e in json_entries:
    ent = entries[e["idx"]]
    text = ent["response"]["content"].get("text", "")
    try:
        data = json.loads(text)
    except Exception as ex:
        print(f"  [{e['idx']}] {e['url'][:100]} NOT JSON: {ex}")
        continue
    if e["url"].endswith(".har") or "har" in e["path"]:
        continue
    print(f"\n[{e['idx']}] {e['method']} {e['url'][:120]} status={e['status']}")
    sch = schema_of(data)
    for line in sch:
        print(f"    {line}")
    json_schemas[e["idx"]] = {"url": e["url"], "schema": sch}

# ---------- 4. HTML FALLBACK: usage data in server-rendered HTML ----------
print("\n== HTML RESPONSES: usage structures ==")
html_entries = [e for e in inventory if e["has_body"] and ("html" in e["mime"].lower() or e["path"] in ("/settings",) or e["path"].startswith("/settings"))]

def find_usage_in_html(html, e):
    """Locate 'Session usage' etc. and capture surrounding DOM."""
    results = []
    patterns = ["Session usage", "session usage", "Monthly usage", "monthly usage", "usage", "Daily", "limit"]
    for pat in ["Session usage", "Monthly usage", "Daily usage"]:
        for m in re.finditer(re.escape(pat), html):
            s = max(0, m.start() - 900)
            en = min(len(html), m.end() + 900)
            results.append((pat, m.start(), html[s:en]))
    return results

for e in html_entries:
    ent = entries[e["idx"]]
    html = ent["response"]["content"].get("text", "") or ""
    print(f"\n[{e['idx']}] {e['method']} {e['url'][:110]} mime={e['mime']} html_len={len(html)}")
    hits = find_usage_in_html(html, e)
    if not hits:
        print("  no 'Session usage'/'Monthly usage' text found")
    for pat, pos, ctx in hits[:4]:
        print(f"\n  --- match '{pat}' @ {pos} (context ±900) ---")
        print(ctx.replace("\n", " ")[:1800])

    # embedded data script tags
    for tag_name, m in [("NEXT_DATA", re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>', html)),
                        ("RENDERED_DATA", re.search(r'<script[^>]+id="(?:__NEXT_DATA__|__remixContext|__NUXT__|__SVELTEKIT__)"', html))]:
        if m:
            print(f"  FOUND {tag_name} script tag at {m.start()}")
    # count script tags and look for JSON-ish big inline scripts
    n_scripts = len(re.findall(r"<script", html))
    print(f"  script tag count: {n_scripts}")
    # look for self.__next_f push streams (Next.js App Router RSC payload)
    if "self.__next_f" in html:
        print("  Next.js RSC payload present (self.__next_f.push(...))")
    # class names near 'Session usage'
    for pat in ["Session usage"]:
        for m in re.finditer(re.escape(pat), html):
            s = max(0, m.start() - 600)
            cls = re.findall(r'class="([^"]{0,300})"', html[s:m.end() + 600])
            print(f"  classes near '{pat}': {cls[-8:]}")

print("\n== DONE PASS 1 ==")