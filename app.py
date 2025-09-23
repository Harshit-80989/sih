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
        st.error("Database connection failed. Check your Streamlit Secrets configuration.")
        st.exception(e)
        st.stop()

db = get_db()

# --- Initialize Session State for UI elements only ---
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = None

# --- DATA HANDLING FUNCTIONS (FIREBASE) ---

@st.cache_data(ttl=300) # Cache data for 5 minutes
def load_data():
    """Load all task data from Firestore."""
    with st.spinner("Syncing tasks from the cloud..."):
        tasks_ref = db.collection("tasks").stream()
        tasks = []
        for task in tasks_ref:
            task_data = task.to_dict()
            task_data['id'] = task.id
            if 'date' in task_data and isinstance(task_data['date'], datetime.datetime):
                 task_data['date'] = pd.to_datetime(task_data['date'])
            tasks.append(task_data)
    return tasks

def save_task(task_description, task_date):
    """Save a new task to Firestore."""
    doc_ref = db.collection("tasks").document()
    doc_ref.set({
        'date': datetime.datetime.combine(task_date, datetime.datetime.min.time()),
        'task': task_description,
        'status': 'pending'
    })
    st.cache_data.clear()

def update_task_status(task_id, is_completed):
    """Update a task's status in Firestore."""
    task_ref = db.collection("tasks").document(task_id)
    new_status = 'completed' if is_completed else 'pending'
    task_ref.update({'status': new_status})
    st.cache_data.clear()

def delete_task(task_id):
    """Delete a task from Firestore."""
    db.collection("tasks").document(task_id).delete()
    st.cache_data.clear()


# --- CORE LOGIC & PLOTTING ---

def calculate_stats(tasks):
    if not tasks:
        return 0, 0, 0, 0, 0
    
    df = pd.DataFrame(tasks)
    df['date'] = pd.to_datetime(df['date'])
    
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
        if unique_dates and (unique_dates[-1] == today or unique_dates[-1] == today - timedelta(days=1)):
            current_streak = 1
            for i in range(len(unique_dates) - 1, 0, -1):
                if unique_dates[i] == unique_dates[i - 1] + timedelta(days=1):
                    current_streak += 1
                else:
                    break
        if not unique_dates or unique_dates[-1] < today - timedelta(days=1):
            current_streak = 0
            
    return completed_df.shape[0], tasks_last_week, total_active_days, max_streak, current_streak

def create_calendar_heatmap(tasks):
    # This function creates the heatmap based on the dates of the tasks
    if not tasks:
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.text(0.5, 0.5, 'No activity to display', ha='center', va='center')
        return fig

    df = pd.DataFrame(tasks)
    df['date'] = pd.to_datetime(df['date'])
    # We create a count for each day a task exists
    daily_counts = df.groupby(df['date'].dt.date).size()
    
    today = datetime.date.today()
    start_date = today - timedelta(weeks=53)
    all_days = pd.date_range(start=start_date, end=today, freq='D')
    # Reindex to create a full calendar, filling missing days with 0
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
    
    categorized_data = heatmap_data.apply(lambda x: x.apply(categorize_counts))

    fig, ax = plt.subplots(figsize=(16, 4))
    sns.heatmap(categorized_data, ax=ax, cmap=custom_cmap, linewidths=1.5, linecolor='white', cbar=False, square=True)
    
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
    ax.set_title("Task Contributions (Last 53 Weeks)", fontsize=16, pad=20)
    plt.tight_layout()
    return fig

def display_task_list(tasks, filter_status):
    st.header("Your Tasks")
    
    if filter_status != 'All':
        display_tasks = [t for t in tasks if t['status'] == filter_status.lower()]
    else:
        display_tasks = tasks
        
    sorted_tasks = sorted(display_tasks, key=lambda x: x['date'], reverse=True)

    if not sorted_tasks:
        st.warning(f"No tasks to display for the filter '{filter_status}'.")
        return

    for task in sorted_tasks:
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        
        with col1:
            is_completed_on_ui = st.checkbox("", value=(task['status'] == 'completed'), key=f"task_{task['id']}")
        
        with col2:
            task_html = f"~~{task['task']}~~" if is_completed_on_ui else task['task']
            st.markdown(f"{task_html} <span style='color:grey; font-size: smaller;'>*(on {task['date'].strftime('%Y-%m-%d')})*</span>", unsafe_allow_html=True)
        
        with col3:
            if st.button("🗑️", key=f"remove_{task['id']}", help="Remove this task"):
                st.session_state.confirm_delete = task
                st.rerun()

        if is_completed_on_ui != (task['status'] == 'completed'):
            update_task_status(task['id'], is_completed_on_ui)
            st.rerun()

# --- Main App UI & Logic ---

tasks = load_data()

# Deletion Modal
if st.session_state.confirm_delete is not None:
    task_to_delete = st.session_state.confirm_delete
    with st.dialog("Confirm Deletion"):
        st.warning(f"Are you sure you want to permanently delete this task?\n\n> {task_to_delete['task']}")
        if st.button("Yes, Delete"):
            delete_task(task_to_delete['id'])
            st.session_state.confirm_delete = None
            st.success("Task deleted.")
            st.rerun()
        if st.button("Cancel"):
            st.session_state.confirm_delete = None
            st.rerun()

# Sidebar Input
st.sidebar.header("Log a New Task")
task_description = st.sidebar.text_input("Task Description:", placeholder="e.g., Solved LeetCode #217")
task_date = st.sidebar.date_input("Completion Date:", datetime.date.today())

if st.sidebar.button("Add Task", type="primary"):
    if task_description:
        with st.spinner("Saving task..."):
            save_task(task_description, task_date)
        st.rerun()
    else:
        st.sidebar.warning("Please enter a task description.")

# Main Page Display
st.title("My LeetCoder Style Task Tracker 🎯")
st.write("Your personal task tracker, powered by the cloud. Data is synced across all devices.")

if not tasks:
    st.info("No tasks logged yet. Add your first task using the sidebar to get started!")
else:
    total_completed, tasks_last_week, total_active_days, max_streak, current_streak = calculate_stats(tasks)
    
    st.header("Your Stats")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks Completed", f"{total_completed}", delta=tasks_last_week)
    col2.metric("Total Active Days", f"{total_active_days}")
    col3.metric("Current Streak", f"⚡ {current_streak} Days")
    col4.metric("Max Streak", f"🔥 {max_streak} Days")
    
    st.markdown("---")
    st.header("Activity Heatmap")
    st.pyplot(create_calendar_heatmap(tasks))
    st.markdown("---")
    
    filter_status = st.selectbox("Filter tasks by status:", ['All', 'Pending', 'Completed'])
    display_task_list(tasks, filter_status)

