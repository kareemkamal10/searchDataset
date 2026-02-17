# Maqam-Matcher

Maqam-Matcher is a Streamlit GUI tool to curate a high-quality dataset of
"Arabic Piano Covers" paired with their original songs for ML training.

Quickstart
----------
1. Create a virtual environment (Python 3.10+)
2. pip install -r requirements.txt
3. streamlit run app.py

Structure
---------
See `piano-dataset-builder/` for a modular, SOLID-aligned layout.

Notes
-----
- Uses `yt-dlp` for fast metadata extraction (no downloads by default).
- Uses `youtubesearchpython` to locate candidate original tracks.
- The dataset export is saved to `data/dataset_output.csv` (UTF-8 safe).
