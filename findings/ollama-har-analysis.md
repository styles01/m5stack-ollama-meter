# Ollama Settings HAR Analysis — Web Data Contract for the M5Stack Usage Meter

**Source:** `/Users/clawdio/.openclaw/workspace/ollama-settings.har` (391,503 bytes, JSON HAR)
**Capture:** 2026-04-24T19:48:47.360Z, Chrome HAR format exported by Safari Web Inspector (`creator: WebInspector 537.36`), single page `https://ollama.com/settings`
**Analysis date:** 2026-09-01
**Security:** No cookie or token values are reproduced in this document — names and structure only.

---

## 1. INVENTORY — every request entry

7 entries total, **all on `ollama.com`** (no third-party trackers, CDNs, or analytics in the capture).

| # | Method | URL | Status | MIME type | Response size | Body captured | Carries usage data? |
|---|--------|-----|--------|-----------|--------------:|:-------------:|---------------------|
| 0 | GET | `https://ollama.com/settings` | 200 | `text/html` | 21,285 B | 21,281 B | **YES — the only entry that matters** |
| 1 | GET | `https://ollama.com/public/tailwind.css?v=e7a7acaa…` | 304 | `text/css` | 69,092 B | 69,092 B | no |
| 2 | GET | `https://ollama.com/public/vendor/prism/prism.css?v=…` | 304 | `text/css` | 1,794 B | 1,794 B | no |
| 3 | GET | `https://ollama.com/public/vendor/htmx/bundle.js` | 304 | `text/javascript` | 89,696 B | 89,696 B | no |
| 4 | GET | `https://ollama.com/public/ollama.png` | 304 | `image/png` | 7,487 B | 9,984 B | no |
| 5 | GET | `https://ollama.com/public/assets/00000000-0000-3000-8000-000000000000.png` | 200 | `image/png` | 120,481 B | 160,644 B | no (account avatar) |
| 6 | GET | `https://ollama.com/public/icon-32x32.png` | 304 | `image/png` | 890 B | 1,188 B | no |

**Domain grouping:** `ollama.com` — 7/7 entries (1 HTML document, 2 CSS, 1 JS, 3 PNG).

**Usage-data URLs:** exactly one — `GET https://ollama.com/settings` (`_resourceType: document`, response header `server: Google Frontend`, `x-build-commit: 13ce878f7887a8b28af55505ccd4e34c854c91e0`, `x-frame-options` present). Page `<title>`: `Usage · Settings`.

**There are NO JSON API calls in this capture.** No `/api/...` XHR/fetch requests at all — the usage numbers are rendered server-side into the initial HTML document. The page uses **htmx** (loaded from `/public/vendor/htmx/bundle.js`) for interactivity, but the settings document itself needs no client-side fetch to display usage.

---

## 2. AUTH MECHANISM

### What the HAR itself shows

The HAR was exported from **Safari's Web Inspector**, which **strips all `Cookie` and `Set-Cookie` headers on export**. Verified programmatically: `cookie` appears in the request-header name list of **0/7 entries**, and every entry's `request.cookies` array is empty. No `Authorization`, `x-csrf-token`, `x-api-key`, or similar header appears on any request (only standard browser headers: `accept`, `user-agent`, `sec-fetch-*`, `sec-ch-ua*`, `referer: https://ollama.com/search`, etc.). No `Set-Cookie` response headers survived either.

So the HAR alone cannot reveal the credential — but two other evidence sources pin it down:

### Where the credential actually lives (corroborating evidence)

1. **The existing Playwright scraper** (`~/.openclaw/workspace/command-center/scripts/ollama-usage-scraper.py`, same target URL) authenticates by loading cookies from `command-center/data/ollama-cookies.json`.
2. **That cookie file contains exactly one cookie: `__Secure-session`** (domain `ollama.com`). No bearer token, no CSRF token, no secondary cookies.

### Conclusion for a headless scraper

- **Auth = a single session cookie: `__Secure-session`** (an HttpOnly/Secure session cookie issued by ollama.com login; it is the whole credential).
- **No Authorization/Bearer flow is visible anywhere** (no `/api/auth` or token endpoint in the capture), and **no CSRF token** appears in the HTML or headers — GET requests are unauthenticated-client-side reads.
- A headless Python service needs only: `GET https://ollama.com/settings` with header `Cookie: __Secure-session=<value>` plus a browser-like `User-Agent`. (No value printed here; the live value is held in `~/.openclaw/workspace/command-center/data/ollama-cookies.json`.)
- The cookie is long-lived: saved 2026-04-27, still valid 2026-08-31 per project memory. When it expires, the only recovery path visible is an interactive browser login (re-save the cookie) — there is no refresh-token endpoint in the HAR.
- Requests come from Google Frontend infra; no Cloudflare bot-wall challenge was observed (`cf-ray` absent in the live check below).

**Live verification (2026-09-01, read-only):** a plain `urllib` GET of `https://ollama.com/settings` with only the `__Secure-session` cookie + browser `User-Agent` returned **HTTP 200** with `Session usage` and `Weekly usage` present in the body. Cookie-authenticated direct HTTP is confirmed working without any browser.

---

## 3. DATA CONTRACT

### 3a. JSON API responses in the HAR: **none exist**

`# json-ish entries: []` — the only inline JSON in the whole capture is a 141-byte `application/ld+json` blob in the HTML head (`{"@context", "@type": "WebSite", "name": "Ollama", "url": "…"}`), which carries no usage data. **There is no `data.usage.sessionTokens`-style JSON path to document — ollama.com exposes no usage JSON endpoint to the browser on this page.** Every usage value arrives as HTML text/attributes.

### 3b. The actual contract: values embedded in server-rendered HTML

All usage data lives in one section of the `/settings` HTML. Extracted values in this capture:

| Field | HAR value | Where in DOM |
|-------|-----------|--------------|
| Plan/tier badge | `max` | badge `<span>` next to "Cloud Usage" heading |
| **Session usage** | `9.7` (% used) | `<span class="text-sm">9.7% used</span>` and bar `style="width: 9.7%"` |
| Session reset | `2026-04-24T22:00:00Z` | `div.local-time[data-time]` attr; visible text "Resets in 2 hours" |
| **Weekly usage** | `35.5` (% used) | `<span class="text-sm">35.5% used</span>` and bar `style="width: 35.5%"` |
| Weekly reset | `2026-04-27T00:00:00Z` | `div.local-time[data-time]`; visible text "Resets in 2 days" |

Semantics:
- Usage is exposed **only as percentages** — no absolute token counts, no remaining credits, no dollar amounts, no model-level quotas, and no separate daily/monthly limits (session + weekly only). "Cloud models and capabilities such as web search contribute to session and weekly limits."
- Session window appears to be ~5h-ish rolling (resets 2h after a 20:00Z capture → next reset 22:00Z; later observation: reset 02:00Z) — treat `data-time` as authoritative, not "daily".
- Weekly window resets Monday 00:00 UTC (capture Thu 2026-04-24 → reset Mon 2026-04-27T00:00Z; latest: 2026-09-07T00:00Z, also a Monday).

### 3c. Downstream JSON contract (scraper output — what the M5Stack service can standardize on)

The existing scraper normalizes the HTML into `command-center/data/ollama-usage.json` (schema verified against the live file):

```json
{
  "sessionUsage": { "percentage": 0.0, "resetAt": "2026-09-01T02:00:00Z" },
  "weeklyUsage":  { "percentage": 34.1, "resetAt": "2026-09-07T00:00:00Z" },
  "lastUpdated":  "2026-08-31T21:02:28.318683+00:00",
  "available": true,
  "error": null
}
```

JSON paths for consumers: `sessionUsage.percentage` (float 0–100), `sessionUsage.resetAt` (ISO-8601 UTC), `weeklyUsage.percentage`, `weeklyUsage.resetAt`, `lastUpdated`, `available` (bool — false on scrape failure), `error` (string|null). Recommended for the M5Stack meter: poll the local JSON/route, not ollama.com directly, at device level.

---

## 4. HTML FALLBACK — DOM structure of the usage section

Full section as captured (from `<h2>Cloud Usage</h2>` through the notify form). Each usage row follows this identical pattern:

```html
<h2 class="text-xl font-medium flex items-center space-x-2">
    <span>Cloud Usage</span>
    <span class="text-xs font-normal px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600 capitalize"
      >max</span>                                    <!-- tier badge -->
</h2>
<p class="text-xs text-neutral-500 mb-4">Cloud models and capabilities … limits.</p>

<div>                                              <!-- one <div> per usage row -->
  <div class="flex justify-between mb-2">
    <span class="text-sm">Session usage</span>     <!-- row label -->
    <span class="text-sm">9.7% used</span>         <!-- percentage -->
  </div>
  <div class="w-full border border-1 border-neutral-200 rounded-full h-2 overflow-hidden">  <!-- bar track -->
    <div class="h-full rounded-full bg-neutral-300" style="width: 9.7%"></div>              <!-- bar fill -->
  </div>
  <div class="text-xs text-neutral-500 mt-1 local-time" data-time="2026-04-24T22:00:00Z">
    Resets in 2 hours                              <!-- human text; data-time is the machine value -->
  </div>
</div>
<!-- … identical block for "Weekly usage" / 35.5% / data-time="2026-04-27T00:00:00Z" … -->

<script>  /* inline: decorates .local-time titles from data-time — no data of its own */  </script>

<form method="POST" action="/settings" class="pt-2" hx-post="/settings" hx-swap="none">
  <label class="flex items-center gap-2 text-xs text-neutral-700">
    <input type="checkbox" name="notify-usage-limits" class="rounded border-neutral-300"
           onchange="this.form.requestSubmit()" checked />
    <span>Notify me when I'm close to hitting my usage limits</span>
  </label>
</form>
```

### Extraction selectors (exact, verified against the captured 21,281-byte body)

- **Section anchor:** `h2` containing `<span>Cloud Usage</span>`
- **Tier:** the `span.capitalize` badge inside that `h2` (class contains `capitalize`)
- **Usage rows:** the `<div>` siblings after the `<p>` description; each row:
  - Label: row `div > div.flex.justify-between.mb-2 > span.text-sm:first-child` → `"Session usage"` / `"Weekly usage"`
  - **Percentage:** row `div > div.flex.justify-between.mb-2 > span.text-sm:last-child` → text like `9.7% used` (regex: `>([\d.]+)%\s*used<`)
  - **Bar fill:** row `div > div[style^="width:"]` → `style="width: 9.7%"` (regex: `width:\s*([\d.]+)%`) — most robust machine-readable form; the row order is **Session, then Weekly**
  - **Reset time:** row `div.local-time[data-time]` → ISO-8601 UTC attribute (never parse the human text "Resets in N hours/days")
- **Single regex pair that extracts both rows** (used successfully by the existing scraper, resilient to whitespace):
  - `Session usage\s*</span>\s*<span[^>]*>([0-9.]+)%\s*used</span>` (then the same for `Weekly usage`)
  - reset times: read `data-time="…"` within each row `<div>` (fallback regexes in the scraper also match `local-time` blocks)

### Embedded script data: **none relevant**

5 `<script>` tags total: (1) `application/ld+json` WebSite schema — no usage data; (2) a 1,279-char inline JS utility; (3) the 903-char `.local-time` decorator; (4) external htmx bundle; (5) a 358-char inline JS. **No `__NEXT_DATA__`, no RSC/`self.__next_f` payload, no embedded JSON state** — the site is server-rendered templates (Google Frontend + htmx), so there is no script-tag JSON path to mine. The percentages appear exactly twice per row (label span + bar `width` style), giving a built-in consistency check: both occurrences must agree.

---

## 5. RECOMMENDATION — cheapest reliable fetch for a small local Python service

**Use direct HTTP with the session cookie. Do not use Playwright.**

Evidence:
1. **All data is in the initial HTML document** — zero XHR/fetch/API requests in the capture; the document body (21 KB) carries everything. No rendering step adds information.
2. **Auth is a single cookie** (`__Secure-session`); no CSRF, no JS-computed tokens, no bearer flow.
3. **Empirically verified (2026-09-01):** plain `urllib` GET + `Cookie: __Secure-session=…` + browser `User-Agent` → HTTP 200 with both usage rows present. The existing 30-min cron scraper relies on Playwright only because it already had a browser context; it is not required.

Recommended implementation (stdlib-only, ~30 lines):

```python
import re, json, urllib.request

cookies = json.load(open("/Users/clawdio/.openclaw/workspace/command-center/data/ollama-cookies.json"))
ck = cookies if isinstance(cookies, list) else cookies.get("cookies", [])
cookie_hdr = "; ".join(f"{c['name']}={c['value']}" for c in ck if "ollama.com" in c.get("domain", ""))

req = urllib.request.Request("https://ollama.com/settings", headers={
    "Cookie": cookie_hdr,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml",
})
html = urllib.request.urlopen(req, timeout=30).read().decode()

def pct(label):
    m = re.search(label + r"\s*</span>\s*<span[^>]*>([0-9.]+)%\s*used</span>", html)
    return float(m.group(1)) if m else None

usage = {
    "sessionUsage": {"percentage": pct("Session usage")},
    "weeklyUsage":  {"percentage": pct("Weekly usage")},
    # resetAt: parse data-time="..." inside each row div
}
```

Operational notes:
- Poll politely (≥5 min interval; the existing 30-min cadence is fine) and serve the normalized JSON (schema in §3c) to the M5Stack over LAN — the device should never hold the ollama.com cookie.
- Parse `data-time` for resets; ignore the "Resets in N…" prose.
- Failure handling: on login-page/redirect (loss of `Session usage` marker), set `available: false` and alert for cookie re-save; the cookie has lasted ≥4 months so far.
- Fragility caveat: selectors are Tailwind utility classes with no semantic ids — anchor the regexes on the stable label texts ("Session usage", "Weekly usage", "% used", `data-time`), not on long class strings, exactly as the existing scraper does.

---

## Compact summary

- **Requests:** 7, all `ollama.com`; usage data only in `GET https://ollama.com/settings` (200, `text/html`, 21 KB). No JSON API endpoints exist for usage.
- **Auth:** single session cookie `__Secure-session` (HAR had cookies stripped by Safari export; name confirmed from `command-center/data/ollama-cookies.json` + live 200 on 2026-09-01). No bearer/CSRF.
- **Key fields:** HTML labels `Session usage` / `Weekly usage` with `N% used` spans; bar `style="width: N%"`; reset times in `div.local-time[data-time]` (ISO-8601 UTC); tier badge "max". No token counts/credits exposed — percentages only.
- **Recommendation:** direct HTTP GET with the cookie (stdlib `urllib`/`requests`), regex/BeautifulSoup extract — Playwright unnecessary; verified live.