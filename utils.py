"""Utility helpers for the Charlotte Daily Family Brief Streamlit app.

This module keeps API logic and local data storage logic separate from UI rendering,
which makes the app easier to maintain and portfolio-friendly.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

# Load .env values once at import time so NEWS_API_KEY is available in app.py.
load_dotenv()

# Charlotte coordinates and timezone for Open-Meteo queries.
LATITUDE = 35.2271
LONGITUDE = -80.8431
TIMEZONE = "America/New_York"

# Local storage paths.
DATA_DIR = Path("data")
GROCERY_PATH = DATA_DIR / "family_grocery.json"
TODO_PATH = DATA_DIR / "family_todo.json"

# Friendly weather label mapping for common WMO weather codes.
WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def ensure_data_files() -> None:
    """Create the local data directory and JSON files if they don't exist.

    We initialize both files as empty arrays to support `st.data_editor` table format.
    """
    DATA_DIR.mkdir(exist_ok=True)

    for path in (GROCERY_PATH, TODO_PATH):
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


@st.cache_data(ttl=1800)
def get_weather_data() -> dict[str, Any] | None:
    """Fetch current and daily weather from Open-Meteo.

    Cached for 30 minutes to improve responsiveness and reduce repeated API calls.
    Returns None when requests fail so UI can fail gracefully.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "current": ["temperature_2m", "relative_humidity_2m", "weather_code"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
        "temperature_unit": "fahrenheit",
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=1800)
def get_air_quality_data() -> dict[str, Any] | None:
    """Fetch current Charlotte air-quality values from Open-Meteo.

    Cached for 30 minutes. Returns None on network/API failure.
    """
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "current": ["us_aqi", "pm2_5", "pm10"],
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=1200)
def get_top_news(news_api_key: str) -> list[dict[str, Any]] | None:
    """Fetch top U.S. headlines from NewsAPI.

    Cached for 20 minutes. If API key is missing or request fails, returns None.
    """
    if not news_api_key:
        return None

    url = "https://newsapi.org/v2/top-headlines"
    params = {"country": "us", "pageSize": 10, "apiKey": news_api_key}

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return payload.get("articles", [])
    except requests.RequestException:
        return None


@st.cache_data(ttl=900)
def get_espn_scoreboard(url: str) -> dict[str, Any] | None:
    """Fetch scoreboard payload from ESPN public endpoints.

    Cached for 15 minutes because game schedules/scores can change during active games.
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def _extract_team_event(
    events: list[dict[str, Any]], team_name: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Find the most recent completed event and nearest upcoming event for a team."""
    past_events: list[tuple[datetime, dict[str, Any]]] = []
    future_events: list[tuple[datetime, dict[str, Any]]] = []

    for event in events:
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])

        team_found = any((comp.get("team") or {}).get("displayName") == team_name for comp in competitors)
        if not team_found:
            continue

        event_date_raw = event.get("date")
        if not event_date_raw:
            continue

        event_date = datetime.fromisoformat(event_date_raw.replace("Z", "+00:00"))
        status_type = ((event.get("status") or {}).get("type") or {}).get("state", "")

        if status_type == "post":
            past_events.append((event_date, event))
        else:
            future_events.append((event_date, event))

    past_events.sort(key=lambda item: item[0], reverse=True)
    future_events.sort(key=lambda item: item[0])

    recent_event = past_events[0][1] if past_events else None
    next_event = future_events[0][1] if future_events else None
    return recent_event, next_event


def parse_team_snapshot(scoreboard: dict[str, Any] | None, team_name: str) -> dict[str, str]:
    """Return a compact game snapshot for rendering team metrics.

    This function normalizes ESPN data into simple strings so UI code stays clean.
    """
    default_snapshot = {
        "recent": "No recent game found",
        "recent_score": "—",
        "opponent": "—",
        "next_game": "No upcoming game found",
    }

    if not scoreboard:
        return default_snapshot

    events = scoreboard.get("events", [])
    if not events:
        return default_snapshot

    recent_event, next_event = _extract_team_event(events, team_name)

    snapshot = default_snapshot.copy()

    if recent_event:
        competition = (recent_event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])

        team_comp = next((c for c in competitors if (c.get("team") or {}).get("displayName") == team_name), None)
        opp_comp = next((c for c in competitors if (c.get("team") or {}).get("displayName") != team_name), None)

        if team_comp and opp_comp:
            team_score = team_comp.get("score", "0")
            opp_score = opp_comp.get("score", "0")
            opponent = (opp_comp.get("team") or {}).get("displayName", "Unknown")
            snapshot["recent"] = recent_event.get("name", "Recent game")
            snapshot["recent_score"] = f"{team_name} {team_score} - {opp_score} {opponent}"
            snapshot["opponent"] = opponent

    if next_event:
        next_date_raw = next_event.get("date", "")
        try:
            next_date = datetime.fromisoformat(next_date_raw.replace("Z", "+00:00"))
            snapshot["next_game"] = next_date.astimezone().strftime("%a, %b %d at %I:%M %p")
        except ValueError:
            snapshot["next_game"] = next_date_raw

    return snapshot


def weather_code_to_text(code: int | None) -> str:
    """Convert Open-Meteo weather code to a human-friendly label."""
    if code is None:
        return "Unknown"
    return WEATHER_CODE_MAP.get(code, f"Code {code}")


def forecast_to_dataframe(weather_data: dict[str, Any]) -> pd.DataFrame:
    """Build a 7-day forecast DataFrame for table/chart display."""
    daily = weather_data.get("daily", {})

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(daily.get("time", [])),
            "High (°F)": daily.get("temperature_2m_max", []),
            "Low (°F)": daily.get("temperature_2m_min", []),
            "Condition": [weather_code_to_text(code) for code in daily.get("weather_code", [])],
        }
    )
    if not df.empty:
        df["Date"] = df["Date"].dt.strftime("%a, %b %d")
    return df


def load_json_rows(path: Path) -> list[dict[str, Any]]:
    """Read row-based JSON safely; returns an empty list on malformed files."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_json_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Persist row-based JSON with pretty indentation for readability."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)
