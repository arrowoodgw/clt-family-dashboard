"""Utility helpers for the Charlotte Daily Family Brief Streamlit app.

This module keeps API logic and local data storage logic separate from UI rendering,
which makes the app easier to maintain and portfolio-friendly.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

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

# Public ESPN scoreboard endpoints (no API key required).
NFL_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
NBA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

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
def get_espn_scoreboard(url: str, dates: str) -> dict[str, Any]:
    """Fetch scoreboard payload from ESPN public endpoints.

    The `dates` range helps return recent and upcoming games when there are no games
    on the current day (common during offseason). This endpoint is public and does not
    require an API key.
    """
    params = {"dates": dates}
    request_url = f"{url}?{urlencode(params)}"

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return {
                "request_url": request_url,
                "events": [],
                "error": f"ESPN returned status code {response.status_code}",
            }

        payload = response.json()
        return {
            "request_url": request_url,
            "events": payload.get("events", []),
            "error": "",
        }
    except requests.RequestException as exc:
        return {
            "request_url": request_url,
            "events": [],
            "error": f"ESPN request failed: {exc}",
        }


def _format_compact_date(date_raw: str) -> str:
    """Format ESPN ISO date strings to concise local display text."""
    try:
        parsed = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%a, %b %d at %I:%M %p")
    except ValueError:
        return date_raw


def _match_team(competitor: dict[str, Any], team_name: str, team_abbr: str) -> bool:
    """Support robust matching by display name substring and abbreviation."""
    team = competitor.get("team") or {}
    display_name = (team.get("displayName") or "").lower()
    short_name = (team.get("shortDisplayName") or "").lower()
    abbreviation = (team.get("abbreviation") or "").lower()

    name_query = team_name.lower()
    abbr_query = team_abbr.lower()

    return (
        name_query in display_name
        or name_query in short_name
        or abbreviation == abbr_query
    )


def _extract_team_games(
    events: list[dict[str, Any]],
    team_name: str,
    team_abbr: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
    """Return most recent completed and next scheduled game for a team."""
    recent_game: tuple[datetime, dict[str, Any]] | None = None
    next_game: tuple[datetime, dict[str, Any]] | None = None
    matched_games = 0

    for event in events:
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])

        team_comp = next((c for c in competitors if _match_team(c, team_name, team_abbr)), None)
        if not team_comp:
            continue

        matched_games += 1

        event_date_raw = event.get("date")
        if not event_date_raw:
            continue

        try:
            event_date = datetime.fromisoformat(event_date_raw.replace("Z", "+00:00"))
        except ValueError:
            continue

        status_type = (event.get("status") or {}).get("type") or {}
        state = status_type.get("state", "")
        is_completed = bool(status_type.get("completed")) or state == "post"
        is_scheduled = state == "pre"

        if is_completed and (recent_game is None or event_date > recent_game[0]):
            recent_game = (event_date, event)

        if is_scheduled and event_date >= datetime.now(timezone.utc):
            if next_game is None or event_date < next_game[0]:
                next_game = (event_date, event)

    return (
        recent_game[1] if recent_game else None,
        next_game[1] if next_game else None,
        matched_games,
    )


def _event_details(event: dict[str, Any], team_name: str, team_abbr: str) -> dict[str, str]:
    """Build human-friendly game details for either recent or upcoming display."""
    competition = (event.get("competitions") or [{}])[0]
    competitors = competition.get("competitors", [])

    team_comp = next((c for c in competitors if _match_team(c, team_name, team_abbr)), None)
    opp_comp = next((c for c in competitors if c is not team_comp), None)

    if not team_comp or not opp_comp:
        return {
            "summary": "Game details unavailable",
            "opponent": "Unknown",
            "location": "",
            "date": _format_compact_date(event.get("date", "")),
        }

    team_score = team_comp.get("score", "0")
    opp_score = opp_comp.get("score", "0")
    opponent = (opp_comp.get("team") or {}).get("displayName", "Unknown")
    is_home = (team_comp.get("homeAway") or "").lower() == "home"
    location = "Home" if is_home else "Away"

    return {
        "summary": f"{team_name} {team_score} - {opp_score} {opponent}",
        "opponent": opponent,
        "location": location,
        "date": _format_compact_date(event.get("date", "")),
    }


def parse_team_snapshot(
    sport: str,
    scoreboard: dict[str, Any],
    team_name: str,
    team_abbr: str,
) -> dict[str, Any]:
    """Normalize ESPN events into a dashboard-friendly sports snapshot."""
    season_message = (
        "NFL offseason. No games scheduled." if sport == "NFL" else "NBA offseason. No games scheduled."
    )

    snapshot: dict[str, Any] = {
        "recent_score": "No recent games in the selected window.",
        "recent_detail": "No completed games found.",
        "next_game": season_message,
        "next_detail": "No upcoming scheduled games found.",
        "request_url": scoreboard.get("request_url", ""),
        "events_count": len(scoreboard.get("events", [])),
        "matched_games_count": 0,
        "error": scoreboard.get("error", ""),
    }

    events = scoreboard.get("events", [])
    if not events:
        return snapshot

    recent_event, next_event, matched_games = _extract_team_games(events, team_name, team_abbr)
    snapshot["matched_games_count"] = matched_games

    if recent_event:
        recent_details = _event_details(recent_event, team_name, team_abbr)
        snapshot["recent_score"] = recent_details["summary"]
        snapshot["recent_detail"] = (
            f"{recent_details['location']} vs {recent_details['opponent']} • {recent_details['date']}"
        )

    if next_event:
        next_details = _event_details(next_event, team_name, team_abbr)
        snapshot["next_game"] = f"{next_details['location']} vs {next_details['opponent']}"
        snapshot["next_detail"] = next_details["date"]

    return snapshot


def get_default_sports_window() -> str:
    """Build a wide date window to cover both recent and upcoming games."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=30)
    end = today + timedelta(days=60)
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"


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
