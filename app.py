import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap
import json
import google.cloud.firestore
from google.oauth2 import service_account

# --- CONFIGURATION & DATABASE CONNECTION ---
st.set_page_config(page_title="Task Tracker", page_icon="✅", layout="wide")

@st.cache_resource
def get_db():
    try:
        key_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        db = google.cloud.firestore.Client(credentials=creds)
        return db
    except Exception as e:
        st.error("Failed to connect to the database. Please check your Streamlit Secrets.")
        st.stop()

db = get_db()

# --- SESSION STATE INITIALIZATION FOR TEMPORARY TASKS ---
today = datetime.date.today()

if 'tasks' not in st.session_state:
    st.session_state.tasks = []
    st.session_state.last_active_date = today

# Automatic daily reset logic
if st.session_state.last_active_date != today:
    st.session_state.tasks = []
    st.session_state.last_active_date = today

if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = None


# --- DATA HANDLING FUNCTIONS ---

@st.cache_data(ttl=600) # Cache the permanent activity log for 10 minutes
def load_activity_log():
    """Load only the dates of activity from Firestore for the heatmap."""
    with st.spinner("Loading activity history..."):
        log_ref = db.collection("activity_log").stream()
        activity_dates = [pd.to_datetime(log.id) for log in log_ref]
    return activity_dates

def log_activity(activity_date):
    """Save a date to the permanent activity log in Firestore. Using date as ID prevents duplicates."""
    date_str = activity_date.strftime('%Y-%m-%d')
    doc_ref = db.collection("activity_log").document(date_str)
    # The set operation is idempotent: running it multiple times has no extra effect.
    doc_ref.set({'recorded': True})
    # Clear the cache so the heatmap updates immediately
    st.cache_data.clear()

def add_task_to_session(task_description, task_date):
    """Adds a task to the temporary session list and logs the permanent activity."""
    # 1. Add to temporary list in session state
    task_id = len(st.session_state.tasks) + 1
    st.session_state.tasks.append({
        'id': task_id,
        'date': task_date,
        'task': task_description,
        'status': 'pending'
    })
    # 2. Log the activity permanently
    log_activity(task_date)

def update_task_in_session(task_id, is_completed):
    """Updates a task's status in the temporary session list."""
    for task in st.session_state.tasks:
        if task['id'] == task_id:
            task['status'] = 'completed' if is_completed else 'pending'
            break

def delete_task_from_session(task_id):
    """Deletes a task from the temporary session list."""
    st.session_state.tasks = [t for t in st.session_state.tasks if t['id'] != task_id]


# --- CORE LOGIC & PLOTTING ---
# Note: These functions now use the permanent `activity_dates` for stats and heatmap

def calculate_stats(activity_dates):
    if not activity_dates:
        return 0, 0, 0
    
    unique_dates = sorted(list(set([d.date() for d in activity_dates])))
    total_active_days = len(unique_dates)

    if not unique_dates:
        return 0, 0, 0
    
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
        if unique_dates[-1] < today - timedelta(days=1):
            current_streak = 0
            
    return total_active_days, max_streak, current_streak

def create_calendar_heatmap(activity_dates):
    if not activity_dates:
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.text(0.5, 0.5, 'No activity data to display', ha='center', va='center')
        return fig

    # We only care about the dates, not the number of tasks per day.
    # So we create a series of 1s for each active day.
    daily_activity = pd.Series(1, index=pd.to_datetime(activity_dates))

    today = datetime.date.today()
    start_date = today - timedelta(weeks=53)
    all_days = pd.date_range(start=start_date, end=today, freq='D')
    # Use reindex to create a full year's calendar, filling non-active days with 0.
    daily_counts = daily_activity.reindex(all_days, fill_value=0)
    
    calendar_data = pd.DataFrame({'counts': daily_counts.values, 'date': daily_counts.index})
    calendar_data['date'] = pd.to_datetime(calendar_data['date'])
    calendar_data['weekday'] = calendar_data['date'].dt.weekday
    calendar_data['week'] = calendar_data['date'].dt.isocalendar().week
    calendar_data['year'] = calendar_data['date'].dt.year
    calendar_data['year_week'] = calendar_data['year'].astype(str) + '-' + calendar_data['week'].astype(str).str.zfill(2)
    
    heatmap_data = calendar_data.pivot_table(index='weekday', columns='year_week', values='counts', fill_value=0).sort_index(axis=1)

    # Simplified color map: 0 for no activity, 1 for any activity.
    colors = ["#ebedf0", "#216e39"] 
    custom_cmap = ListedColormap(colors)
    
    fig, ax = plt.subplots(figsize=(16, 4))
    sns.heatmap(heatmap_data, ax=ax, cmap=custom_cmap, linewidths=1.5, linecolor='white', cbar=False, square=True)
    
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], rotation=0)
    # ... (rest of heatmap formatting is the same)
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
    ax.set_title("Activity Contributions (Last 53 Weeks)", fontsize=16, pad=20)
    plt.tight_layout()
    return fig

# --- UI DISPLAY FUNCTIONS ---
# Note: This function now uses the temporary `st.session_state.tasks`

def display_task_list(filter_status):
    st.header(f"Today's Tasks")
    
    if filter_status != 'All':
        display_tasks = [t for t in st.session_state.tasks if t['status'] == filter_status.lower()]
    else:
        display_tasks = st.session_state.tasks
        
    if not display_tasks:
        st.info(f"No tasks to display for today. Add one to get started!")
        return

    for task in reversed(display_tasks): # Show newest first
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        
        with col1:
            is_completed_on_ui = st.checkbox("", value=(task['status'] == 'completed'), key=f"task_{task['id']}")
        
        with col2:
            task_html = f"~~{task['task']}~~" if is_completed_on_ui else task['task']
            st.markdown(task_html, unsafe_allow_html=True)
        
        with col3:
            if st.button("🗑️", key=f"remove_{task['id']}", help="Remove this task"):
                st.session_state.confirm_delete = task
                st.rerun()

        if is_completed_on_ui != (task['status'] == 'completed'):
            update_task_in_session(task['id'], is_completed_on_ui)
            st.rerun()

# --- MAIN APP ---

activity_dates = load_activity_log()

# Deletion Modal
if st.session_state.confirm_delete is not None:
    task_to_delete = st.session_state.confirm_delete
    with st.dialog("Confirm Deletion"):
        st.warning(f"Are you sure you want to delete this task from today's list?\n\n> {task_to_delete['task']}")
        if st.button("Yes, Delete"):
            delete_task_from_session(task_to_delete['id'])
            st.session_state.confirm_delete = None
            st.rerun()
        if st.button("Cancel"):
            st.session_state.confirm_delete = None
            st.rerun()

# Sidebar
st.sidebar.header("Log a New Task for Today")
task_description = st.sidebar.text_input("Task Description:", placeholder="e.g., Solved LeetCode #217")
if st.sidebar.button("Add Task", type="primary"):
    if task_description:
        add_task_to_session(task_description, datetime.date.today())
        st.rerun()
    else:
        st.sidebar.warning("Please enter a task description.")

# Main Page
st.title("My LeetCoder Style Task Tracker 🎯")
st.write("Add tasks for today. Your activity heatmap is saved permanently, but the task list resets each day.")

total_active_days, max_streak, current_streak = calculate_stats(activity_dates)
st.header("Your Permanent Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Total Active Days", f"{total_active_days}")
col2.metric("Current Streak", f"⚡ {current_streak} Days")
col3.metric("Max Streak", f"🔥 {max_streak} Days")

st.markdown("---")
st.header("Activity Heatmap")
st.pyplot(create_calendar_heatmap(activity_dates))
st.markdown("---")

filter_status = st.selectbox("Filter today's tasks:", ['All', 'Pending', 'Completed'])
display_task_list(filter_status)

