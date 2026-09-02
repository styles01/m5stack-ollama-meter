#!/usr/bin/env python3
"""Pass 2: deep-dive the /settings HTML — usage section, script tags, auth hints, headers."""
import json, re

HAR = "/Users/clawdio/.openclaw/workspace/ollama-settings.har"
with open(HAR, "r", encoding="utf-8", errors="replace") as f:
    har = json.load(f)
entries = har["log"]["entries"]

ent0 = entries[0]
html = ent0["response"]["content"].get("text", "")

# 1. Full Cloud Usage section: from <h2 ...>Cloud Usage to the next <h2 or sidebar end
m = re.search(r"<h2[^>]*>\s*<span>Cloud Usage</span>", html)
if m:
    start = m.start()
    nxt = re.search(r"<h2", html[start + 10:])
    end = start + 10 + (nxt.start() if nxt else 6000)
    section = html[start:min(end, start + 8000)]
    print("=== FULL CLOUD USAGE SECTION ===")
    print(section)

# 2. All percentage labels + data-time attributes
print("\n=== PERCENT/LABEL/TIME EXTRACTION ===")
for m2 in re.finditer(r'<span class="text-sm">([^<]+)</span>\s*<span class="text-sm">([^<]+)</span>', html):
    print(f"  row: {m2.group(1).strip()!r} | {m2.group(2).strip()!r}")
for m2 in re.finditer(r'bar-width:?\s*([\d.]+)%', html):
    print(f"  bar-width: {m2.group(1)}%")
for m2 in re.finditer(r'style="width: ([\d.]+)%"', html):
    print(f"  inline width: {m2.group(1)}%")
for m2 in re.finditer(r'data-time="([^"]+)"[^>]*>([^<]*)<', html):
    print(f"  data-time: {m2.group(1)} -> text {m2.group(2).strip()!r}")
for m2 in re.finditer(r'Resets in[^<]*', html):
    print(f"  reset text: {m2.group(0).strip()!r}")

# 3. Script tags: attributes + inline JSON check
print("\n=== SCRIPT TAGS ===")
for m2 in re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.S):
    attrs, body = m2.group(1), m2.group(2).strip()
    src = re.search(r'src="([^"]+)"', attrs)
    kind = "external" if src else "inline"
    is_json = body[:1] in "{["
    print(f"  {kind}: src={src.group(1) if src else '-'} attrs={attrs.strip()[:100]} inline_len={len(body)} starts_json={is_json}")
    if is_json and body:
        try:
            d = json.loads(body)
            print(f"    parsed JSON top-level keys: {list(d.keys())[:20]}")
        except Exception as ex:
            print(f"    json parse fail: {ex}; head: {body[:120]!r}")

# 4. Auth hints anywhere in HTML
print("\n=== AUTH HINTS IN HTML ===")
for pat in [r'csrf', r'x-csrf', r'authenticity', r'name="token"', r'logout', r'sign\s?out', r'"user"', r'cookie']:
    hits = [m2.start() for m2 in re.finditer(pat, html, re.I)]
    print(f"  '{pat}': {len(hits)} hits at {hits[:6]}")
mm = re.search(r'<title>([^<]*)</title>', html)
print(f"  <title>: {mm.group(1) if mm else '?'}")
# account identifier strings (redact but show shape)
for m2 in re.finditer(r'(href="(/settings[^"]*|/[-\w]+)")', html):
    pass
# look for logged-in username element
mm = re.search(r'Logged in as[^<]*<', html)
print(f"  'Logged in as': {mm.group(0)[:60] if mm else 'not found'}")

# 5. Response headers (names only) for entry 0 + request 'referer'
print("\n=== ENTRY 0 RESPONSE HEADER NAMES ===")
print([h["name"] for h in ent0["response"].get("headers", [])])
print("request referer:", next((h["value"] for h in ent0["request"]["headers"] if h["name"].lower() == "referer"), None))
print("request accept:", next((h["value"][:80] for h in ent0["request"]["headers"] if h["name"].lower() == "accept"), None))

# 6. Do ANY entries carry a cookie header at all?
print("\n=== COOKIE HEADER PRESENCE ACROSS ALL ENTRIES ===")
for i, e in enumerate(entries):
    names = [h["name"].lower() for h in e["request"].get("headers", [])]
    print(f"  [{i}] {e['request']['url'][:70]}: cookie_in_headers={'cookie' in names}, har_cookies={len(e['request'].get('cookies', []))}")

# 7. pages / timings metadata
print("\n=== HAR PAGES ===")
for p in har["log"].get("pages", []):
    print(f"  id={p.get('id')} title={p.get('_name') or p.get('title')}")
# any _resourceType etc
print("entry0 keys:", list(ent0.keys()))
print("entry0 _resourceType:", ent0.get("_resourceType"))
print("\n=== OTHER ENTRY REQ HEADER NAMES (1) ===")
print([h["name"] for h in entries[1]["request"].get("headers", [])])