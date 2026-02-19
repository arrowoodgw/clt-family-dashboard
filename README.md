# Charlotte Daily Family Brief

A privacy-first, local-only Streamlit dashboard designed for a Charlotte, NC family to check each morning.

This app combines:
- Weather and air quality in Charlotte
- Top U.S. headlines
- Panthers & Hornets game snapshots
- Shared grocery and to-do lists with local autosave

No cloud deployment, no database, no Docker—just `streamlit run app.py` on your local machine.

---

## Screenshot

> _Add a screenshot here after launching locally._

```markdown
![Charlotte Daily Family Brief Screenshot](docs/screenshot.png)
```

---

## Features

- **100% local runtime** with Streamlit
- **Local JSON persistence** for grocery and todo data
- **Cached API calls** for speed and reduced network load
- **Graceful error handling** for missing keys and API outages
- **Modern Streamlit UI** with tabs, metrics, editors, and expanders

---

## Tech Stack

- Python 3.10+
- Streamlit
- Requests
- Pandas
- Plotly
- python-dotenv

---

## Quick Start

### 1) Clone the repository

```bash
git clone <your-repo-url>
cd charlotte-family-brief
```

### 2) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Create your environment file

```bash
cp .env.example .env
```

### 5) Add your NewsAPI key

Edit `.env` and set:

```env
NEWS_API_KEY=your_real_key_here
```

### 6) Run the app

```bash
streamlit run app.py
```

---

## Local Data Storage

The app automatically creates JSON files inside `data/` if they are missing:

- `data/family_grocery.json`
- `data/family_todo.json`

These files are git-ignored so your household data stays local.

---

## macOS Desktop Shortcut (Open Dashboard Fast)

### Option A: Save as a Browser Favorite
1. Run the app with `streamlit run app.py`
2. Open the local URL (usually `http://localhost:8501`)
3. Add it to your browser favorites/bookmarks bar as **Charlotte Daily Family Brief**

### Option B: Create a macOS Shortcut app
1. Open the **Shortcuts** app on macOS
2. Create a new shortcut named **Charlotte Daily Family Brief**
3. Add action: **Open URLs** → `http://localhost:8501`
4. (Optional) Add action: **Run Shell Script** to start Streamlit before opening URL:
   ```bash
   cd /path/to/charlotte-family-brief && source .venv/bin/activate && streamlit run app.py
   ```
5. Pin the shortcut to Dock/Menu Bar for one-click launch

---

## Notes

- News requires a valid key from [NewsAPI.org](https://newsapi.org/).
- Sports data is pulled from ESPN public scoreboard endpoints and does **not** require an API key.
- Weather and AQI data are pulled from Open-Meteo public APIs.

## Sports troubleshooting

If the sports panel looks empty, it may be offseason for one or both teams. The app now surfaces explicit offseason/no-scheduled-games messaging instead of leaving blank fields.

---

Built for my Charlotte family — feel free to fork!
