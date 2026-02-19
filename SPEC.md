# 🌅 Charlotte Daily Family Brief
## Product Specification (SPEC.md)

---

## 1. Overview

Project Name: charlotte-family-brief  
Type: Local Streamlit Dashboard  
Primary Users: A family in Charlotte, NC  
Runtime Environment: Local machine (Mac/iPad/Desktop via browser)  
Deployment: None (runs locally with `streamlit run app.py`)

---

## 2. Vision

Create a simple, beautiful, privacy-first daily dashboard that consolidates:

- Weather & air quality
- Top U.S. headlines
- Local professional sports updates
- Shared grocery & to-do lists

The dashboard should feel lightweight, useful, and pleasant to open each morning — like a digital family command center.

---

## 3. Design Principles

- Local-first: No cloud deployment, no database
- Privacy-first: Only public APIs + local JSON storage
- Low friction: One command to run
- Readable & modular: Portfolio-grade code quality
- Resilient: Graceful handling of API errors
- Fast: Aggressive caching using `@st.cache_data`

---

## 4. Technical Requirements

### Language & Environment
- Python 3.10+
- Streamlit

### Libraries
- streamlit
- requests
- pandas
- python-dotenv
- plotly

### Environment Variables
- NEWS_API_KEY (stored in `.env`)

---

## 5. Application Layout

The application must use:

st.set_page_config(layout="wide")

Top-level UI:

- Title: 🌅 Charlotte Daily Family Brief
- Caption: Current date (formatted nicely)
- Four tabs with emojis (exact order required)

---

## 6. Functional Requirements

### 6.1 🌤️ Weather & Air

Weather API: Open-Meteo  
- Latitude: 35.2271  
- Longitude: -80.8431  
- Timezone: America/New_York  

Display:
- Current temperature (°F)
- Humidity
- Weather condition (converted to friendly text)
- 7-day high/low forecast

Forecast must be displayed via:
- Pandas DataFrame OR
- Plotly chart

Air Quality API: Open-Meteo Air Quality  

Display:
- US AQI
- PM2.5
- PM10

Include a friendly note about Charlotte pollen season.

---

### 6.2 📰 Top News

Source: NewsAPI.org  
Endpoint: top-headlines?country=us  

Requirements:
- Pull top 10 U.S. headlines
- Display each headline inside an expander
- Expander must show:
  - Description
  - Source
  - Published date
  - Clickable URL

Gracefully handle:
- Missing API key
- Failed API requests

---

### 6.3 🏈 Panthers & Hornets

Source: ESPN Public APIs  

NFL:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard

NBA:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard

Display for:
- Carolina Panthers
- Charlotte Hornets

Show:
- Most recent game
- Score
- Opponent
- Next scheduled game (if available)

Handle off-season or no-game cases gracefully.

---

### 6.4 📋 Grocery & Todo

#### Grocery List

- Implement with `st.data_editor`
- Allow dynamic rows
- Autosave to: data/family_grocery.json
- Create file automatically if missing

---

#### Todo List

Columns:
- Task (text)
- Done (checkbox)

Behavior:
- Autosave to: data/family_todo.json
- Only persist unfinished tasks
- Remove completed tasks automatically

---

## 7. Data Storage

All persistent data must be stored locally in:

data/

Files:
- family_grocery.json
- family_todo.json

These must:
- Be automatically created if missing
- Be ignored by git (but keep the folder)

---

## 8. Performance & Caching

All external API calls must use:

@st.cache_data(ttl=...)

Suggested TTL values:
- Weather: 30 minutes
- Air quality: 30 minutes
- News: 15–30 minutes
- Sports: 15 minutes

---

## 9. Error Handling

The app must:

- Use try/except for API calls
- Display user-friendly error messages
- Use loading spinners while fetching data
- Fail gracefully without crashing the entire app

---

## 10. Non-Goals

- No authentication
- No cloud hosting
- No database
- No Docker
- No CI/CD (for now)

---

## 11. Future Enhancements (Optional Roadmap)

- Calendar integration
- School lunch menus
- Local Charlotte news filter
- Traffic updates
- Smart notifications
- Theme toggle (dark mode)

---

## 12. Definition of Done

The project is complete when:

- `streamlit run app.py` works locally
- All four tabs load successfully
- API calls are cached
- Grocery & todo lists persist correctly
- Code is modular and portfolio-ready
- README contains setup instructions

---

Built for my Charlotte family — and as a portfolio demonstration of clean, local-first dashboard engineering.
