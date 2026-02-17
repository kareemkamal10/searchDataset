# Maqam-Matcher

A local Streamlit GUI application to curate a dataset of **Arabic Piano Covers**
paired with their **Original Songs** for AI training.

## Workflow

1. **Input** — Paste a YouTube Channel or Playlist URL.
2. **Fetch & Classify** — Fetch all video metadata; classify as *Shorts* (≤ 60 s) or *Full Videos*.
3. **Intelligent Matching** — Analyse each title, search YouTube for the original track.
4. **Human-in-the-Loop Review** — Side-by-side curation grid with include/exclude checkboxes, manual overrides, and confidence scores.
5. **Export** — Generate a clean `data/dataset_output.csv`.

## Quick Start

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

## Project Structure

```
maqam_matcher/
├── src/
│   ├── __init__.py      # Package marker
│   ├── fetcher.py       # yt-dlp wrapper — playlists & channels
│   ├── classifier.py    # Shorts vs Full Video classification
│   ├── matcher.py       # Title cleaning → YouTube search → scoring
│   └── utils.py         # Regex helpers, time formatting, constants
├── data/
│   └── dataset_output.csv
├── config/
│   └── settings.py      # Optional project-wide constants
├── tests/               # pytest tests (to be added)
├── app.py               # Streamlit entry point
├── requirements.txt
└── README.md
```

## Tech Stack

| Component        | Library                     |
|------------------|-----------------------------|
| UI               | Streamlit                   |
| Data fetching    | yt-dlp (metadata-only)      |
| Search engine    | youtube-search-python       |
| Data handling    | pandas                      |

## Notes

- **No API keys required** — `youtube-search-python` scrapes public results.
- **No audio downloads** — only JSON metadata is fetched for speed.
- The dataset CSV is saved with `utf-8-sig` encoding for safe Arabic text handling.
