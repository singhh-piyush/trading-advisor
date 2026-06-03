# Trading Advisor

A free, always-on news-triage dashboard. A scheduled GitHub Actions job pulls
market news (general/trending + your watchlist), runs it through Groq
(Llama 3.3 70B) to flag which tickers each story likely affects and in which
direction, and commits the result. A static page renders it. No server, no paid tier.

**What it is:** a ranked "where should I look today" feed.
**What it is not:** a buy/sell signal. News is usually priced in within seconds;
this surfaces and sorts it so you can do your own research. Not financial advice.

---

## Setup (about 10 minutes)

### 1. Create the repo
Put these files in a **public** GitHub repo. Public matters: it gives you
unlimited free Actions minutes and free GitHub Pages. Your API keys live in
encrypted secrets, never in the repo, so public is safe here.

### 2. Get the free API keys
- **Groq** — https://console.groq.com/keys (email signup, no card). Free tier is
  ~30 requests/min and ~1,000/day, far more than one run every 30 min needs.
- **Finnhub** — https://finnhub.io/register (free, 60 requests/min, includes news).
- **Marketaux** *(optional)* — https://www.marketaux.com for extra international
  coverage. Leave it off if you don't want it.

### 3. Add them as repository secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `GROQ_API_KEY`
- `FINNHUB_API_KEY`
- `MARKETAUX_API_KEY` *(only if you enabled it in `config.json`)*

### 4. Edit your watchlist
In `config.json`, set `watchlist` to the tickers you care about. Toggle sources
on/off in `sources`, and swap the `rss_feeds` if any go stale.

### 5. Turn on GitHub Pages
Repo → **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
branch `main`, folder `/ (root)`. Your site will be at
`https://<your-username>.github.io/<repo-name>/`.

### 6. Run it once
Repo → **Actions** tab → enable workflows if prompted → select
**Update Trading Radar** → **Run workflow**. That generates the first live
`results.json` and pushes it. After that it runs on its own every ~30 minutes.

Open your Pages URL and you should see live signals instead of the sample data.

---

## How it works

```
GitHub Actions (cron, every ~30 min)
        │
        ├─ Finnhub general news      ─┐
        ├─ Finnhub company news       │  gather + dedup headlines
        ├─ RSS feeds (CNBC, etc.)     │  (each source fails soft)
        ├─ Reddit hot posts           │
        └─ Marketaux (optional)      ─┘
        │
        └─ one Groq call → {ticker, direction, confidence, reason, headline}
                │
                └─ commit results.json → GitHub Pages serves it
                        │
                        └─ index.html renders Watchlist + On-the-Radar
```

## Tuning notes
- **Schedule:** edit the `cron` in `.github/workflows/update.yml`. GitHub runs
  scheduled jobs best-effort, so they can fire late or skip under load — normal.
- **Token budget:** Groq's free tier caps tokens-per-minute, so `analyze.py`
  trims to `max_headlines` (default 45) and caps each ticker's news. If you want
  to feed in far more headlines, Google's Gemini free tier has a much higher
  token-per-minute ceiling — swap the `call_groq` endpoint/model to use it.
- **Reddit:** the public `.json` endpoints sometimes block datacenter IPs like
  Actions runners. If Reddit fails in the logs, that's expected; everything else
  still runs. Set `"reddit": false` to silence it.
- **Hallucination guardrails:** the prompt forbids inventing tickers/headlines,
  trusts Finnhub's ticker hints, and the parser drops anything that isn't a valid
  ticker shape. Confidence is deliberately conservative.

## Run locally (optional)
```bash
pip install -r requirements.txt
export GROQ_API_KEY=...  FINNHUB_API_KEY=...
python analyze.py
python -m http.server 8000   # then open http://localhost:8000
```

---

*For research and learning only. Nothing here is investment advice.*
