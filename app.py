import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap
import os

# --- CONFIGURATION ---
TASK_DATA_FILE = "tasks.csv"
st.set_page_config(page_title="Task Tracker", page_icon="✅", layout="wide")

# --- Initialize Session State ---
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = None # Stores the index of the task to be deleted

# --- DATA HANDLING FUNCTIONS (LOCAL CSV) ---

def load_data():
    """Load task data from CSV, create file if it doesn't exist, and add 'status' column if missing."""
    if not os.path.exists(TASK_DATA_FILE):
        df = pd.DataFrame(columns=['date', 'task', 'status'])
        df.to_csv(TASK_DATA_FILE, index=False)
    
    df = pd.read_csv(TASK_DATA_FILE, parse_dates=['date'])
    
    if 'status' not in df.columns:
        df['status'] = 'completed' # Backward compatibility for old files
    
    return df

def save_data(df):
    """Save the DataFrame to the CSV file."""
    df.to_csv(TASK_DATA_FILE, index=False)


# --- CORE LOGIC & PLOTTING (No changes needed here) ---

def calculate_stats(df):
    if df.empty:
        return 0, 0, 0, 0, 0

    completed_df = df[df['status'] == 'completed']
    unique_dates = sorted(df['date'].dt.date.unique())
    total_active_days = len(unique_dates)

    one_week_ago = datetime.date.today() - timedelta(days=7)
    tasks_last_week = completed_df[completed_df['date'].dt.date > one_week_ago].shape[0]

    if not unique_dates:
        return completed_df.shape[0], tasks_last_week, 0, 0, 0
    
    max_streak = 0
    if total_active_days > 0:
        max_streak = 1
        current_streak_calc = 1
        for i in range(1, len(unique_dates)):
            if unique_dates[i] == unique_dates[i - 1] + timedelta(days=1):
                current_streak_calc += 1
            else:
                current_streak_calc = 1
            if current_streak_calc > max_streak:
                max_streak = current_streak_calc
    
    current_streak = 0
    if unique_dates:
        today = datetime.date.today()
        if unique_dates[-1] == today or unique_dates[-1] == today - timedelta(days=1):
            current_streak = 1
            for i in range(len(unique_dates) - 1, 0, -1):
                if unique_dates[i] == unique_dates[i - 1] + timedelta(days=1):
                    current_streak += 1
                else:
                    break
        # If the last active day was not today or yesterday, the streak is broken
        if unique_dates[-1] < today - timedelta(days=1):
            current_streak = 0
            
    return completed_df.shape[0], tasks_last_week, total_active_days, max_streak, current_streak

def display_badges(max_streak):
    st.header("Your Badges")
    badge_svg_template = """<div style="text-align: center; border: 2px solid #e1e4e8; border-radius: 10px; padding: 15px; margin: 5px; background-color: #f6f8fa;"><svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L3 5V11C3 16.5 6.8 21.7 12 23C17.2 21.7 21 16.5 21 11V5L12 2Z" fill="#F9E076" stroke="#B47D00" stroke-width="1"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="7px" font-weight="bold" fill="#B47D00">{days}</text><text x="50%" y="65%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="5px" fill="#B47D00">Days</text></svg><p style="font-weight: bold; margin-top: 5px; color: #24292e;">{days} Day Streak</p></div>"""
    milestones = [50, 100, 150, 200, 250, 300, 365]
    badges_earned = [m for m in milestones if max_streak >= m]

    if not badges_earned:
        st.info("Keep up the great work! Your first badge unlocks at a 50-day streak.")
        return
    
    cols = st.columns(len(badges_earned))
    for i, milestone in enumerate(badges_earned):
        with cols[i]:
            st.markdown(badge_svg_template.format(days=milestone), unsafe_allow_html=True)

def create_calendar_heatmap(df):
    if df.empty:
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.text(0.5, 0.5, 'No data to display', ha='center', va='center')
        return fig

    plot_df = df.copy()
    plot_df['date'] = pd.to_datetime(plot_df['date'])
    daily_counts = plot_df.groupby(plot_df['date'].dt.date).size()
    
    today = datetime.date.today()
    start_date = today - timedelta(weeks=53)
    all_days = pd.date_range(start=start_date, end=today, freq='D')
    daily_counts = daily_counts.reindex(all_days.date, fill_value=0)
    
    calendar_data = pd.DataFrame({'counts': daily_counts.values, 'date': daily_counts.index})
    calendar_data['date'] = pd.to_datetime(calendar_data['date'])
    calendar_data['weekday'] = calendar_data['date'].dt.weekday
    calendar_data['week'] = calendar_data['date'].dt.isocalendar().week
    calendar_data['year'] = calendar_data['date'].dt.year
    calendar_data['year_week'] = calendar_data['year'].astype(str) + '-' + calendar_data['week'].astype(str).str.zfill(2)
    
    heatmap_data = calendar_data.pivot_table(index='weekday', columns='year_week', values='counts', fill_value=0).sort_index(axis=1)

    colors = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
    custom_cmap = ListedColormap(colors)
    
    def categorize_counts(count):
        if count == 0: return 0
        elif 1 <= count <= 2: return 1
        elif 3 <= count <= 5: return 2
        elif 6 <= count <= 8: return 3
        else: return 4
    
    categorized_data = heatmap_data.applymap(categorize_counts)

    fig, ax = plt.subplots(figsize=(16, 4))
    sns.heatmap(categorized_data, ax=ax, cmap=custom_cmap, linewidths=1.5, linecolor='white', cbar=False, square=True, vmin=0, vmax=len(colors)-1)
    
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], rotation=0)
    ax.set_xlabel('')
    ax.set_ylabel('')
    
    month_labels, month_positions = [], []
    last_month = -1
    for i, year_week in enumerate(heatmap_data.columns):
        year, week = map(int, year_week.split('-'))
        week_date = datetime.datetime.strptime(f'{year}-{week}-1', "%Y-%W-%w")
        if week_date.month != last_month:
            month_labels.append(week_date.strftime('%b'))
            month_positions.append(i)
            last_month = week_date.month

    ax.set_xticks(month_positions)
    ax.set_xticklabels(month_labels)
    ax.set_title("Task Contributions (Last 53 Weeks)", fontsize=16, pad=20)
    plt.tight_layout()
    return fig

def display_task_list(df, filter_status):
    st.header("Recent Tasks")
    if filter_status != 'All':
        display_df = df[df['status'] == filter_status.lower()].copy()
    else:
        display_df = df.copy()
    
    sorted_df = display_df.sort_values(by='date', ascending=False)
    
    if sorted_df.empty:
        st.warning(f"No tasks with status '{filter_status}'.")
        return

    for index, row in sorted_df.iterrows():
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        
        with col1:
            is_completed = st.checkbox("", value=(row['status'] == 'completed'), key=f"task_{index}")
        
        with col2:
            task_html = f"~~{row['task']}~~" if is_completed else row['task']
            st.markdown(f"{task_html} <span style='color:grey; font-size: smaller;'>*(on {row['date'].strftime('%Y-%m-%d')})*</span>", unsafe_allow_html=True)
        
        with col3:
            if st.button("🗑️", key=f"remove_{index}", help="Remove this task"):
                st.session_state.confirm_delete = index
                st.rerun()

        if is_completed != (row['status'] == 'completed'):
            df.loc[index, 'status'] = 'completed' if is_completed else 'pending'
            save_data(df)
            st.rerun()

# --- Main App UI & Logic ---

df = load_data()

# --- Deletion Confirmation Modal ---
if st.session_state.confirm_delete is not None:
    task_to_delete_index = st.session_state.confirm_delete
    task_description = df.loc[task_to_delete_index, 'task']
    with st.dialog("Confirm Deletion"):
        st.warning(f"Are you sure you want to delete this task? \n\n> {task_description}")
        col1, col2 = st.columns(2)
        if col1.button("Yes, Delete"):
            df = df.drop(task_to_delete_index).reset_index(drop=True)
            save_data(df)
            st.session_state.confirm_delete = None
            st.success("Task deleted.")
            st.rerun()
        if col2.button("Cancel"):
            st.session_state.confirm_delete = None
            st.rerun()

# --- Sidebar Input ---
st.sidebar.header("Log a New Task")
task_description = st.sidebar.text_input("Task Description:", placeholder="e.g., Solved LeetCode #217")
task_date = st.sidebar.date_input("Completion Date:", datetime.date.today())

if st.sidebar.button("Add Task", type="primary"):
    if task_description:
        new_task = pd.DataFrame([{'date': pd.to_datetime(task_date), 'task': task_description, 'status': 'pending'}])
        df = pd.concat([df, new_task], ignore_index=True)
        save_data(df)
        st.sidebar.success(f"Added task: '{task_description}'")
        st.rerun()
    else:
        st.sidebar.warning("Please enter a task description.")

# --- Main Page Display ---
st.title("My LeetCoder Style Task Tracker 🎯")
st.write("Your personal task tracker. All data is saved locally on this device.")

if df.empty:
    st.info("No tasks logged yet. Add your first task using the sidebar to get started!")
else:
    total_completed, tasks_last_week, total_active_days, max_streak, current_streak = calculate_stats(df)
    
    st.header("Your Stats")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks Completed", f"{total_completed}", delta=tasks_last_week)
    col2.metric("Total Active Days", f"{total_active_days}")
    col3.metric("Current Streak", f"⚡ {current_streak} Days")
    col4.metric("Max Streak", f"🔥 {max_streak} Days")
    
    st.markdown("---")
    display_badges(max_streak)
    st.markdown("---")
    st.header("Activity Heatmap")
    st.pyplot(create_calendar_heatmap(df))
    st.markdown("---")
    
    filter_status = st.selectbox("Filter tasks by status:", ['All', 'Pending', 'Completed'])
    display_task_list(df, filter_status)

