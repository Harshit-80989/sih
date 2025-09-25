import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap
import json
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Persistent Tracker", page_icon="💾", layout="wide")

# --- FILE-BASED PERSISTENCE ---
DATA_FILE = "progress.json"

def save_completed_dates(dates):
    """Saves the list of completed dates to a local JSON file."""
    # Convert datetime.date objects to strings in 'YYYY-MM-DD' format for JSON serialization
    dates_as_strings = [d.strftime('%Y-%m-%d') for d in dates]
    with open(DATA_FILE, 'w') as f:
        json.dump(dates_as_strings, f)

def load_completed_dates():
    """Loads the list of completed dates from the local JSON file."""
    if not os.path.exists(DATA_FILE):
        return []  # Return an empty list if the file doesn't exist yet
    try:
        with open(DATA_FILE, 'r') as f:
            dates_from_strings = json.load(f)
            # Convert strings back to datetime.date objects
            return [datetime.datetime.strptime(d_str, '%Y-%m-%d').date() for d_str in dates_from_strings]
    except (json.JSONDecodeError, TypeError):
        # If the file is empty or corrupted, start fresh
        return []


# --- SESSION STATE INITIALIZATION ---
# Load the dates from the file into session state ONLY when the app first starts.
if 'completed_dates' not in st.session_state:
    st.session_state.completed_dates = load_completed_dates()


# --- CORE PLOTTING LOGIC ---

def create_completion_heatmap(completed_dates):
    """Generates a heatmap where a day is green only if it's in the completed_dates list."""
    today = datetime.date.today()
    start_date = today - timedelta(weeks=53)
    all_days = pd.date_range(start=start_date, end=today, freq='D')

    daily_data = pd.Series(0, index=all_days)
    for dt in completed_dates:
        if pd.Timestamp(dt) in daily_data.index:
            daily_data[pd.Timestamp(dt)] = 1

    calendar_data = pd.DataFrame({'completed': daily_data, 'date': daily_data.index})
    calendar_data['date'] = pd.to_datetime(calendar_data['date'])
    calendar_data['weekday'] = calendar_data['date'].dt.weekday
    calendar_data['week'] = calendar_data['date'].dt.isocalendar().week
    calendar_data['year'] = calendar_data['date'].dt.year
    calendar_data['year_week'] = calendar_data['year'].astype(str) + '-' + calendar_data['week'].astype(str).str.zfill(2)

    heatmap_data = calendar_data.pivot_table(index='weekday', columns='year_week', values='completed', fill_value=0).sort_index(axis=1)

    colors = ["#ebedf0", "#40c463"]  # Light Gray, Green
    custom_cmap = ListedColormap(colors)

    fig, ax = plt.subplots(figsize=(16, 4))
    sns.heatmap(heatmap_data, ax=ax, cmap=custom_cmap, linewidths=1.5, linecolor='white', cbar=False, square=True)

    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], rotation=0)
    ax.set_xlabel('')
    ax.set_ylabel('')

    month_labels, month_positions = [], []
    last_month = -1
    for i, year_week in enumerate(heatmap_data.columns):
        year, week = map(int, year_week.split('-'))
        try:
            week_date = datetime.datetime.strptime(f'{year}-{week}-1', "%Y-%W-%w")
            if week_date.month != last_month:
                month_labels.append(week_date.strftime('%b'))
                month_positions.append(i)
                last_month = week_date.month
        except ValueError:
            continue

    ax.set_xticks(month_positions)
    ax.set_xticklabels(month_labels)
    ax.set_title("Daily Progress", fontsize=16, pad=20)
    plt.tight_layout()
    return fig


# --- Main App UI ---
st.title("Persistent Daily Tracker 💾")
st.write("Your progress is now saved locally in `progress.json`. Click the button to mark today's square green.")

today = datetime.date.today()

if st.button(f"Mark Today as Complete ✅ ({today.strftime('%B %d, %Y')})"):
    if today not in st.session_state.completed_dates:
        st.session_state.completed_dates.append(today)
        # Save the updated list to the file immediately
        save_completed_dates(st.session_state.completed_dates)
        st.success("Progress saved! Great work.")
        # Rerun to show the updated chart instantly
        st.rerun()
    else:
        st.info("Today is already marked as complete!")

st.markdown("---")

st.pyplot(create_completion_heatmap(st.session_state.completed_dates))
