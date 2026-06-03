#!/usr/bin/env python3
"""
Trading Radar — pulls market news (trending + your watchlist) from free
sources, runs it through Groq (Llama 3.3 70B) to flag likely-affected tickers
and direction, and writes results.json for the static dashboard to render.

Built to run for free on GitHub Actions.

Required env vars (set as GitHub Actions secrets):
    GROQ_API_KEY      - https://console.groq.com/keys   (free, no card)
    FINNHUB_API_KEY   - https://finnhub.io/register      (free, 60 req/min)
Optional:
    MARKETAUX_API_KEY - https://www.marketaux.com        (free tier, extra coverage)

Every news source fails soft: if one is down or rate-limited, the run
continues on whatever else it managed to gather. The LLM call is the only
hard requirement.
"""

import os
import re
import sys
import json
import time
import datetime as dt

import requests

try:
    import feedparser
except ImportError:
    feedparser = None

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
OUTPUT_PATH = os.path.join(ROOT, "results.json")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")
MARKETAUX_API_KEY = os.environ.get("MARKETAUX_API_KEY")  # optional

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

UA = {"User-Agent": "trading-radar/1.0 (personal news triage)"}


def log(msg):
    stamp = dt.datetime.utcnow().isoformat(timespec="seconds")
    print(f"[{stamp}Z] {msg}", flush=True)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Fetchers — each returns a list of {headline, source, url, ticker_hint, ts}
# and swallows its own errors so one bad source never kills the run.
# --------------------------------------------------------------------------

def fetch_finnhub_general(limit=30):
    if not FINNHUB_API_KEY:
        return []
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": FINNHUB_API_KEY},
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for a in r.json()[:limit]:
            related = (a.get("related") or "").split(",")[0].strip().upper()
            out.append({
                "headline": (a.get("headline") or "").strip(),
                "source": a.get("source") or "Finnhub",
                "url": a.get("url") or "",
                "ticker_hint": related or None,
                "ts": int(a.get("datetime") or 0),
            })
        return [x for x in out if x["headline"]]
    except Exception as e:
        log(f"finnhub/general failed: {e}")
        return []


def fetch_finnhub_company(symbol, per_ticker=5):
    if not FINNHUB_API_KEY:
        return []
    today = dt.date.today()
    start = today - dt.timedelta(days=3)
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": symbol,
                "from": start.isoformat(),
                "to": today.isoformat(),
                "token": FINNHUB_API_KEY,
            },
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for a in r.json()[:per_ticker]:
            out.append({
                "headline": (a.get("headline") or "").strip(),
                "source": a.get("source") or "Finnhub",
                "url": a.get("url") or "",
                "ticker_hint": symbol.upper(),
                "ts": int(a.get("datetime") or 0),
            })
        return [x for x in out if x["headline"]]
    except Exception as e:
        log(f"finnhub/company {symbol} failed: {e}")
        return []


def fetch_rss(feeds, per_feed=8):
    if not feedparser:
        log("feedparser not installed; skipping RSS")
        return []
    out = []
    for url in feeds:
        try:
            d = feedparser.parse(url)
            title = d.feed.get("title", "RSS") if getattr(d, "feed", None) else "RSS"
            for e in d.entries[:per_feed]:
                out.append({
                    "headline": (getattr(e, "title", "") or "").strip(),
                    "source": title,
                    "url": getattr(e, "link", "") or "",
                    "ticker_hint": None,
                    "ts": 0,
                })
        except Exception as ex:
            log(f"rss {url} failed: {ex}")
    return [x for x in out if x["headline"]]


def fetch_reddit(subs, per_sub=10):
    out = []
    for sub in subs:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json",
                params={"limit": per_sub},
                headers=UA,
                timeout=20,
            )
            r.raise_for_status()
            for child in r.json().get("data", {}).get("children", []):
                p = child.get("data", {})
                if p.get("stickied"):
                    continue
                out.append({
                    "headline": (p.get("title") or "").strip(),
                    "source": f"r/{sub}",
                    "url": "https://www.reddit.com" + (p.get("permalink") or ""),
                    "ticker_hint": None,
                    "ts": int(p.get("created_utc") or 0),
                })
        except Exception as e:
            log(f"reddit {sub} failed (Actions IPs are sometimes blocked, that's fine): {e}")
    return [x for x in out if x["headline"]]


def fetch_marketaux(limit=15):
    if not MARKETAUX_API_KEY:
        return []
    try:
        r = requests.get(
            "https://api.marketaux.com/v1/news/all",
            params={
                "language": "en",
                "filter_entities": "true",
                "limit": limit,
                "api_token": MARKETAUX_API_KEY,
            },
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for a in r.json().get("data", []):
            ents = a.get("entities") or []
            hint = ents[0]["symbol"].upper() if ents and ents[0].get("symbol") else None
            out.append({
                "headline": (a.get("title") or "").strip(),
                "source": a.get("source") or "Marketaux",
                "url": a.get("url") or "",
                "ticker_hint": hint,
                "ts": 0,
            })
        return [x for x in out if x["headline"]]
    except Exception as e:
        log(f"marketaux failed: {e}")
        return []


# --------------------------------------------------------------------------
# Dedup
# --------------------------------------------------------------------------

def dedup(items):
    seen, out = set(), []
    for it in items:
        key = re.sub(r"\W+", "", it["headline"].lower())[:80]
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


# --------------------------------------------------------------------------
# LLM triage
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a markets news-triage analyst. You receive a numbered list of \
real news headlines. Decide which ones are tradable signals and which ticker each \
most likely affects.

Hard rules:
- Use ONLY the headlines provided. Never invent headlines, tickers, prices, or facts.
- Assign a ticker only if the headline clearly implies that specific company/asset. \
For broad macro/market news with no single clear name, use the most relevant index or \
sector ETF (SPY, QQQ, DIA, XLE, XLF, etc.) or omit the item.
- Some headlines include [hint:TICKER]. Trust the hint unless the headline clearly contradicts it.
- "direction" is the likely SHORT-TERM price move implied by the news, not your personal view.
- Be conservative with confidence. Most news is already priced in by the time it is published.

Return ONLY a JSON object of the form {"items": [ ... ]} with no prose and no code fences.
Each element of "items":
{
  "ticker": "AAPL",
  "company": "short name or empty string",
  "direction": "up" | "down" | "neutral",
  "confidence": 0-100,
  "reason": "one short sentence, max ~15 words",
  "headline_indices": [<integer>, ...]
}
"headline_indices" must list every headline index (from the numbered list above) that \
supports this call — one or more. Use only indices that actually exist; never invent any.
Include at most 25 items, highest confidence first. Omit anything with no tradable angle."""


def call_groq(headlines, watchlist):
    numbered = []
    for i, h in enumerate(headlines):
        hint = f" [hint:{h['ticker_hint']}]" if h.get("ticker_hint") else ""
        numbered.append(f"{i}. {h['headline']}{hint} (via {h['source']})")
    user = (
        f"Watchlist tickers: {', '.join(watchlist) if watchlist else '(none)'}\n\n"
        "Headlines:\n" + "\n".join(numbered)
    )
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    for attempt in range(2):
        r = requests.post(GROQ_URL, headers=headers, json=body, timeout=60)
        if r.status_code == 429 and attempt == 0:
            log("groq rate-limited, waiting 20s then retrying once")
            time.sleep(20)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    r.raise_for_status()


def parse_llm(content):
    content = (content or "").strip()
    content = re.sub(r"^```(?:json)?", "", content).strip()
    content = re.sub(r"```$", "", content).strip()
    try:
        data = json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except Exception:
            return []
    if isinstance(data, list):
        return data
    items = data.get("items", [])
    return items if isinstance(items, list) else []


def collect_indices(it, n):
    """Coalesce the headline index/indices an LLM item cites, tolerating both
    the new "headline_indices": [..] and a legacy single "headline_index": int.
    Returns de-duplicated, in-range integer indices in their original order."""
    raw = it.get("headline_indices")
    if not isinstance(raw, list):
        raw = [it.get("headline_index")]
    seen, out = set(), []
    for idx in raw:
        if isinstance(idx, bool):  # bool is an int subclass; reject it
            continue
        if isinstance(idx, int) and 0 <= idx < n and idx not in seen:
            seen.add(idx)
            out.append(idx)
    return out


def _article_key(h):
    """Dedup key for an article: prefer its url, fall back to the headline."""
    return (h.get("url") or "").strip().lower() or re.sub(
        r"\W+", "", (h.get("headline") or "").lower())[:80]


def build_results(raw_items, headlines, watchlist):
    wl = {t.upper() for t in watchlist}
    out = []
    for it in raw_items:
        try:
            ticker = str(it.get("ticker", "")).upper().strip().lstrip("$")
            if not re.match(r"^[A-Z][A-Z.\-]{0,6}$", ticker):
                continue
            direction = it.get("direction", "neutral")
            if direction not in ("up", "down", "neutral"):
                direction = "neutral"
            try:
                conf = int(round(float(it.get("confidence", 0))))
            except (TypeError, ValueError):
                conf = 0
            conf = max(0, min(100, conf))

            # Articles the AI actually cited, then full coverage for the ticker.
            articles, seen = [], set()

            def add(h, used_by_ai):
                key = _article_key(h)
                if not key or key in seen:
                    return
                seen.add(key)
                articles.append({
                    "headline": h.get("headline", ""),
                    "source": h.get("source", ""),
                    "url": h.get("url", ""),
                    "used_by_ai": used_by_ai,
                })

            for idx in collect_indices(it, len(headlines)):
                add(headlines[idx], True)
            for h in headlines:
                if (h.get("ticker_hint") or "").upper() == ticker:
                    add(h, False)

            breakdown = {}
            for a in articles:
                name = a["source"] or "—"
                breakdown[name] = breakdown.get(name, 0) + 1

            # Primary article keeps the legacy top-level fields populated:
            # first AI-cited one, else first of any, else empty.
            primary = next((a for a in articles if a["used_by_ai"]),
                           articles[0] if articles else {})

            out.append({
                "ticker": ticker,
                "company": str(it.get("company", "")).strip()[:40],
                "direction": direction,
                "confidence": conf,
                "reason": str(it.get("reason", "")).strip()[:180],
                "headline": primary.get("headline", ""),
                "source": primary.get("source", ""),
                "url": primary.get("url", ""),
                "on_watchlist": ticker in wl,
                "articles": articles,
                "source_breakdown": breakdown,
            })
        except Exception as e:
            log(f"skipped malformed item: {e}")
    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    if not GROQ_API_KEY:
        log("ERROR: GROQ_API_KEY is not set. Add it as a repository secret.")
        sys.exit(1)

    cfg = load_config()
    watchlist = [t.upper() for t in cfg.get("watchlist", [])]
    src = cfg.get("sources", {})
    max_headlines = int(cfg.get("max_headlines", 45))

    headlines = []
    if src.get("finnhub_general", True):
        headlines += fetch_finnhub_general()
    if src.get("rss", True):
        headlines += fetch_rss(cfg.get("rss_feeds", []))
    if src.get("reddit", True):
        headlines += fetch_reddit(cfg.get("subreddits", []))
    if src.get("marketaux", False):
        headlines += fetch_marketaux()
    if src.get("finnhub_company", True):
        for tk in watchlist:
            headlines += fetch_finnhub_company(tk)
            time.sleep(0.2)  # stay polite under the 60 req/min free limit

    headlines = dedup(headlines)
    headlines.sort(key=lambda x: x.get("ts", 0), reverse=True)
    headlines = headlines[:max_headlines]
    log(f"collected {len(headlines)} unique headlines")

    if not headlines:
        log("no headlines gathered; keeping previous results.json")
        return

    content = call_groq(headlines, watchlist)
    items = build_results(parse_llm(content), headlines, watchlist)
    log(f"LLM returned {len(items)} usable signals")

    payload = {
        "updated_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "watchlist": watchlist,
        "count": len(items),
        "sample": False,
        "items": items,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    log(f"wrote {len(items)} signals to results.json")


if __name__ == "__main__":
    main()
