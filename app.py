"""Streamlit app entrypoint for Charlotte Daily Family Brief.

UI rendering lives here, while API/data helpers are intentionally split into utils.py.
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import (
    GROCERY_PATH,
    TODO_PATH,
    ensure_data_files,
    forecast_to_dataframe,
    get_air_quality_data,
    get_espn_scoreboard,
    get_top_news,
    get_weather_data,
    load_json_rows,
    parse_team_snapshot,
    save_json_rows,
    weather_code_to_text,
)

# Wide layout improves readability for metric-heavy dashboards.
st.set_page_config(page_title="Charlotte Daily Family Brief", page_icon="🌅", layout="wide")

# Ensure local JSON files exist on startup before any read/write operations.
ensure_data_files()

# Header section.
st.title("🌅 Charlotte Daily Family Brief")
st.caption(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}")
st.write("")

# Required tab order and naming.
tab_weather, tab_news, tab_sports, tab_lists = st.tabs(
    ["🌤️ Weather & Air", "📰 Top News", "🏈 Panthers & Hornets", "📋 Grocery & Todo"]
)

with tab_weather:
    st.subheader("Charlotte Weather Snapshot")

    with st.spinner("Fetching Charlotte weather and air quality..."):
        weather_data = get_weather_data()
        air_data = get_air_quality_data()

    if weather_data:
        current = weather_data.get("current", {})

        c1, c2, c3 = st.columns(3)
        c1.metric("Temperature", f"{current.get('temperature_2m', '—')} °F")
        c2.metric("Humidity", f"{current.get('relative_humidity_2m', '—')}%")
        c3.metric("Conditions", weather_code_to_text(current.get("weather_code")))

        st.markdown("#### 7-Day Forecast")
        forecast_df = forecast_to_dataframe(weather_data)

        left, right = st.columns([1, 2])
        with left:
            st.dataframe(forecast_df, use_container_width=True, hide_index=True)

        with right:
            if not forecast_df.empty:
                chart_source = forecast_df.copy()
                chart_source["High (°F)"] = pd.to_numeric(chart_source["High (°F)"], errors="coerce")
                chart_source["Low (°F)"] = pd.to_numeric(chart_source["Low (°F)"], errors="coerce")

                fig = px.line(
                    chart_source,
                    x="Date",
                    y=["High (°F)", "Low (°F)"],
                    markers=True,
                    title="Charlotte 7-Day Temperature Trend",
                )
                fig.update_layout(legend_title_text="Series", xaxis_title="Day", yaxis_title="Temperature (°F)")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Weather data is currently unavailable. Please try again shortly.")

    st.markdown("---")
    st.subheader("Air Quality")

    if air_data:
        air_current = air_data.get("current", {})
        a1, a2, a3 = st.columns(3)
        a1.metric("US AQI", air_current.get("us_aqi", "—"))
        a2.metric("PM2.5", air_current.get("pm2_5", "—"))
        a3.metric("PM10", air_current.get("pm10", "—"))
    else:
        st.warning("Air-quality data is temporarily unavailable.")

    st.info(
        "Charlotte note: spring pollen can spike quickly here—on high-allergen days, "
        "consider closing windows early and checking meds before heading out."
    )

with tab_news:
    st.subheader("Top U.S. Headlines")
    news_api_key = os.getenv("NEWS_API_KEY", "")

    if not news_api_key:
        st.warning("No NEWS_API_KEY found. Add it to your .env file to load headlines.")
    else:
        with st.spinner("Loading top headlines..."):
            articles = get_top_news(news_api_key)

        if articles is None:
            st.error("Could not fetch headlines right now. Please verify your key and try again.")
        elif not articles:
            st.info("No headlines were returned at the moment.")
        else:
            for idx, article in enumerate(articles[:10], start=1):
                title = article.get("title") or f"Headline {idx}"
                with st.expander(f"{idx}. {title}"):
                    st.write(article.get("description") or "No description available.")
                    st.write(f"**Source:** {(article.get('source') or {}).get('name', 'Unknown')}")
                    st.write(f"**Published:** {article.get('publishedAt', 'Unknown')}")

                    url = article.get("url")
                    if url:
                        st.markdown(f"[Read full article]({url})")

with tab_sports:
    st.subheader("Carolina Teams Snapshot")

    nfl_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    nba_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

    with st.spinner("Fetching latest Panthers and Hornets info..."):
        nfl_data = get_espn_scoreboard(nfl_url)
        nba_data = get_espn_scoreboard(nba_url)

    panthers = parse_team_snapshot(nfl_data, "Carolina Panthers")
    hornets = parse_team_snapshot(nba_data, "Charlotte Hornets")

    col_panthers, col_hornets = st.columns(2)

    with col_panthers:
        st.markdown("### 🐾 Carolina Panthers")
        st.metric("Recent Score", panthers["recent_score"])
        st.write(f"**Opponent:** {panthers['opponent']}")
        st.write(f"**Most Recent Game:** {panthers['recent']}")
        st.write(f"**Next Game:** {panthers['next_game']}")

    with col_hornets:
        st.markdown("### 🐝 Charlotte Hornets")
        st.metric("Recent Score", hornets["recent_score"])
        st.write(f"**Opponent:** {hornets['opponent']}")
        st.write(f"**Most Recent Game:** {hornets['recent']}")
        st.write(f"**Next Game:** {hornets['next_game']}")

with tab_lists:
    st.subheader("Shared Family Lists")

    # Grocery section.
    st.markdown("### 🛒 Grocery List")
    grocery_rows = load_json_rows(GROCERY_PATH)
    grocery_df = pd.DataFrame(grocery_rows or [{"Item": "", "Quantity": "", "Notes": ""}])

    edited_grocery = st.data_editor(
        grocery_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="grocery_editor",
    )

    # Remove fully blank rows before saving to keep JSON clean.
    clean_grocery = edited_grocery.fillna("")
    clean_grocery = clean_grocery[
        (clean_grocery.astype(str).apply(lambda col: col.str.strip())).any(axis=1)
    ]
    save_json_rows(GROCERY_PATH, clean_grocery.to_dict(orient="records"))
    st.caption("Grocery list autosaves locally to data/family_grocery.json")

    st.markdown("---")

    # Todo section.
    st.markdown("### ✅ Family Todo")
    todo_rows = load_json_rows(TODO_PATH)
    todo_df = pd.DataFrame(todo_rows or [{"Task": "", "Done": False}])

    if "Done" not in todo_df.columns:
        todo_df["Done"] = False
    todo_df["Done"] = todo_df["Done"].astype(bool)

    edited_todo = st.data_editor(
        todo_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="todo_editor",
    )

    # Persist only unfinished tasks as requested; completed rows are removed automatically.
    edited_todo = edited_todo.fillna({"Task": "", "Done": False})
    unfinished = edited_todo[
        (edited_todo["Task"].astype(str).str.strip() != "") & (~edited_todo["Done"])
    ][["Task", "Done"]]

    save_json_rows(TODO_PATH, unfinished.to_dict(orient="records"))
    st.caption("Todo list autosaves locally; completed tasks are removed from storage.")

    with st.expander("How local autosave works"):
        st.write(
            "Both editors write directly to JSON files in the local data/ folder on each rerun. "
            "This keeps family list data private to your machine."
        )
