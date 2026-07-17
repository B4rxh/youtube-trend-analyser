# 📡 YouTube Trend Console

A Streamlit app that scrapes recent uploads from YouTube channels via Bright Data,
then uses a two-agent CrewAI pipeline (analysis → synthesis) to generate a
structured trend report — executive summary, trend breakdown, and content
recommendations.

## Project structure

```
.
├── app.py                     # Streamlit UI + pipeline orchestration
├── config.yaml                # CrewAI agent/task definitions
├── brightdata_scrapper.py     # Bright Data API helper functions
├── requirements.txt
├── .gitignore
├── .env.example                # Copy to .env and fill in your keys
├── .streamlit/config.toml     # App theme (dark "Signal Console")
├── assets/                    # Header logos — REPLACE THESE (see below)
│   ├── crewai.png
│   └── brightdata.png
└── transcripts/                # Video transcripts land here at runtime
```

## 1. Replace the placeholder logos

`assets/crewai.png` and `assets/brightdata.png` in this zip are **plain text
placeholders**, not the real brand logos (trademarked assets can't be
auto-generated for you). Before deploying, swap them out for the actual
logos — same filenames, same folder — from crewai.com and brightdata.com,
or from the original tutorial repo this project is based on
(`patchy631/ai-engineering-hub` → `Youtube-trend-analysis/assets`).

## 2. Get your API keys

- **Bright Data**: sign up at brightdata.com → Account Settings → API Keys
  → Add API key → copy it immediately (shown once).
- **OpenAI**: platform.openai.com → Billing (add a card, set a spend limit)
  → API Keys → Create new secret key.

Copy `.env.example` to `.env` and fill both in:

```bash
cp .env.example .env
```

```
BRIGHT_DATA_API_KEY=your_bright_data_key_here
OPENAI_API_KEY=your_openai_key_here
```

## 3. Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Test with **one channel** and a **short date range** first — scraping and
analysis both cost real API usage.

## 4. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: YouTube Trend Console"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.env` is excluded by `.gitignore` — your keys never get committed.

## 5. Deploy on Streamlit Community Cloud

1. share.streamlit.io → sign in with GitHub → **New app**
2. Select this repo/branch, set **Main file path** to `app.py`
3. Advanced settings → **Secrets** → paste:
   ```toml
   BRIGHT_DATA_API_KEY = "your-key-here"
   OPENAI_API_KEY = "your-key-here"
   ```
4. **Deploy**

Every subsequent `git push` to `main` auto-redeploys the live app.

## Known limits to plan around

- Bright Data's scrape/poll loop (`time.sleep(10)` in `app.py`) can take
  several minutes for larger channel batches — watch for platform timeouts
  on free hosting tiers.
- `brightdata_scrapper.py` shells out to `curl` via `subprocess` — present
  by default on Streamlit Cloud, but check for it if you containerize this
  yourself elsewhere.
- `config.yaml`'s tasks expect the report to come back with `## Executive
  Summary`, `## Trend Breakdown`, and `## Content Recommendations` headings
  exactly — the tabbed report UI in `app.py` parses on those headings.
