import streamlit as st
import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap
import google.cloud.firestore
import json

# --- CONFIGURATION & DATABASE CONNECTION ---

# This line uses Streamlit's secrets management to get your Firebase credentials
# You will set this up in the Streamlit Cloud dashboard
key_dict = json.loads(st.secrets["textkey"])
creds = google.oauth2.service_account.Credentials.from_service_account_info(key_dict)
db = google.cloud.firestore.Client(credentials=creds, project="task-tracker-app")


# --- DATA HANDLING FUNCTIONS (NOW WITH FIREBASE) ---

@st.cache_data(ttl=300) # Cache the data for 5 minutes
def load_data():
    """Load task data from Firestore, returning a list of dictionaries."""
    tasks_ref = db.collection("tasks").stream()
    tasks = [task.to_dict() for task in tasks_ref]
    # Ensure dates are proper datetime objects
    for task in tasks:
        task['date'] = task['date'].date()
    return tasks

def save_task(task_description, task_date):
    """Save a new task to Firestore."""
    doc_ref = db.collection("tasks").document()
    doc_ref.set({
        'id': doc_ref.id,
        'date': datetime.datetime.combine(task_date, datetime.datetime.min.time()),
        'task': task_description,
        'status': 'pending'
    })

def update_task_status(task_id, new_status):
    """Update the status of an existing task."""
    db.collection("tasks").document(task_id).update({'status': new_status})

def delete_task(task_id):
    """Delete a task from Firestore."""
    db.collection("tasks").document(task_id).delete()


# --- All other functions (calculate_stats, display_badges, create_calendar_heatmap, etc.) remain the same ---
# They will now receive a list of dictionaries instead of a pandas DataFrame,
# but the logic inside them is adapted to handle this.

def calculate_stats(tasks):
    """Calculate key statistics from the list of tasks."""
    if not tasks:
        return 0, 0, 0, 0, 0

    completed_tasks = [t for t in tasks if t['status'] == 'completed']
    unique_dates = sorted(list(set(t['date'] for t in tasks)))
    total_active_days = len(unique_dates)
    
    one_week_ago = datetime.date.today() - timedelta(days=7)
    tasks_last_week = len([t for t in completed_tasks if t['date'] > one_week_ago])

    if not unique_dates:
        return len(completed_tasks), tasks_last_week, 0, 0, 0

    # Max streak calculation
    max_streak = 0
    if total_active_days > 0:
        max_streak = 1
        current_streak = 1
        for i in range(1, len(unique_dates)):
            if unique_dates[i] == unique_dates[i - 1] + timedelta(days=1):
                current_streak += 1
            else:
                current_streak = 1
            if current_streak > max_streak:
                max_streak = current_streak
    
    # Current streak calculation
    current_streak_calc = 0
    if unique_dates:
        today = datetime.date.today()
        if unique_dates[-1] == today or unique_dates[-1] == today - timedelta(days=1):
            current_streak_calc = 1
            for i in range(len(unique_dates) - 1, 0, -1):
                if unique_dates[i] == unique_dates[i - 1] + timedelta(days=1):
                    current_streak_calc += 1
                else:
                    break
    
    return len(completed_tasks), tasks_last_week, total_active_days, max_streak, current_streak_calc

def display_badges(max_streak):
    """Displays streak badges based on the user's max streak."""
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

def create_calendar_heatmap(tasks):
    """Creates a GitHub/LeetCode-style calendar heatmap from the task data."""
    if not tasks:
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.text(0.5, 0.5, 'No data to display', ha='center', va='center')
        return fig
    
    import pandas as pd # Import pandas only for plotting
    plot_df = pd.DataFrame(tasks)
    plot_df['date'] = pd.to_datetime(plot_df['date'])
    daily_counts = plot_df.groupby(plot_df['date'].dt.date).size()
    
    today = datetime.date.today()
    start_date = today - timedelta(weeks=53)
    all_days = pd.date_range(start=start_date, end=today, freq='D')
    
    daily_counts = daily_counts.reindex(all_days.date, fill_value=0)

    calendar_data = pd.DataFrame({
        'counts': daily_counts.values,
        'date': daily_counts.index
    })
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


def display_task_list(tasks, filter_status):
    """Displays the interactive task list with filtering and actions."""
    st.header("Recent Tasks")
    if filter_status != 'All':
        display_tasks = [t for t in tasks if t['status'] == filter_status.lower()]
    else:
        display_tasks = tasks
    
    sorted_tasks = sorted(display_tasks, key=lambda x: x['date'], reverse=True)
    
    if not sorted_tasks:
        st.warning(f"No tasks with status '{filter_status}'.")
        return

    for task in sorted_tasks:
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        task_id = task['id']

        with col1:
            is_completed = st.checkbox("", value=(task['status'] == 'completed'), key=f"task_{task_id}")
        
        with col2:
            task_html = f"~~{task['task']}~~" if is_completed else task['task']
            st.markdown(f"{task_html} <span style='color:grey; font-size: smaller;'>*(on {task['date'].strftime('%Y-%m-%d')})*</span>", unsafe_allow_html=True)
        
        with col3:
            if st.button("🗑️", key=f"remove_{task_id}", help="Remove this task"):
                delete_task(task_id)
                st.rerun()

        if is_completed != (task['status'] == 'completed'):
            new_status = 'completed' if is_completed else 'pending'
            update_task_status(task_id, new_status)
            st.rerun()

# --- SIDEBAR & MAIN PAGE LOGIC (Mostly unchanged) ---

st.sidebar.header("Log a New Task")
task_description = st.sidebar.text_input("Task Description:", placeholder="e.g., Solved LeetCode #217")
task_date = st.sidebar.date_input("Completion Date:", datetime.date.today())

if st.sidebar.button("Add Task", type="primary"):
    if task_description:
        with st.spinner("Adding task..."):
            save_task(task_description, task_date)
            st.sidebar.success(f"Added task: '{task_description}'")
            st.cache_data.clear() # Clear cache to reload data
            st.rerun()
    else:
        st.sidebar.warning("Please enter a task description.")

st.title("My LeetCoder Style Task Tracker 🎯")
st.write("Your centralized task tracker. Data is now synced across all devices.")

tasks = load_data()

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
    display_badges(max_streak)
    st.markdown("---")
    st.header("Activity Heatmap")
    st.pyplot(create_calendar_heatmap(tasks))
    st.markdown("---")
    
    filter_status = st.selectbox("Filter tasks by status:", ['All', 'Pending', 'Completed'])
    display_task_list(tasks, filter_status)

