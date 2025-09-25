import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap

# --- CONFIGURATION ---
st.set_page_config(page_title="Task Completion Status", page_icon="🟢", layout="wide")

# --- STATIC DATA SOURCE ---
def get_static_tasks():
    """
    Creates a hardcoded list of tasks with different statuses and dates.
    This replaces any database or user input.
    """
    today = datetime.date.today()
    tasks = [
        {'id': 1, 'task': 'Draft project proposal', 'status': 'completed', 'date': today - timedelta(days=3)},
        {'id': 2, 'task': 'Review Q3 budget', 'status': 'completed', 'date': today - timedelta(days=10)},
        {'id': 3, 'task': 'Send follow-up emails', 'status': 'pending', 'date': today - timedelta(days=10)},
        {'id': 4, 'task': 'Finalize marketing slides', 'status': 'completed', 'date': today - timedelta(days=15)},
        {'id': 5, 'task': 'Plan team offsite', 'status': 'pending', 'date': today - timedelta(days=15)},
        {'id': 6, 'task': 'Research new software', 'status': 'pending', 'date': today - timedelta(days=20)},
        {'id': 7, 'task': 'Submit expense report', 'status': 'completed', 'date': today - timedelta(days=25)},
        {'id': 8, 'task': 'Onboard new hire', 'status': 'completed', 'date': today - timedelta(days=30)},
        {'id': 9, 'task': 'Update project roadmap', 'status': 'completed', 'date': today - timedelta(days=31)},
        {'id': 10, 'task': 'Prepare for client meeting', 'status': 'pending', 'date': datetime.date.today()}
    ]
    
    # Convert dates to datetime objects
    for task in tasks:
        task['date'] = datetime.datetime.combine(task['date'], datetime.datetime.min.time())
        
    return tasks

# --- CORE PLOTTING LOGIC (MODIFIED) ---

def create_completion_heatmap(tasks):
    """
    Generates a heatmap where a day is green if it has ANY completed tasks,
    otherwise it's white/gray.
    """
    if not tasks:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No tasks to display', ha='center', va='center')
        return fig

    df = pd.DataFrame(tasks)
    df['date'] = pd.to_datetime(df['date'])

    # *** KEY CHANGE: Filter for ONLY completed tasks before counting ***
    completed_df = df[df['status'] == 'completed']
    
    # Count occurrences of completed tasks for each day
    daily_completions = completed_df.groupby(completed_df['date'].dt.date).size()
    
    today = datetime.date.today()
    start_date = today - timedelta(weeks=53)
    all_days = pd.date_range(start=start_date, end=today, freq='D')
    
    # Reindex to create a full calendar, filling missing days with 0 completions
    daily_completions = daily_completions.reindex(all_days.date, fill_value=0)
    
    # Convert counts to a simple 0 (no completion) or 1 (completion)
    # This ensures a single color for any day with a completed task.
    completion_binary = (daily_completions > 0).astype(int)
    
    calendar_data = pd.DataFrame({'completed': completion_binary, 'date': completion_binary.index})
    calendar_data['date'] = pd.to_datetime(calendar_data['date'])
    calendar_data['weekday'] = calendar_data['date'].dt.weekday
    calendar_data['week'] = calendar_data['date'].dt.isocalendar().week
    calendar_data['year'] = calendar_data['date'].dt.year
    calendar_data['year_week'] = calendar_data['year'].astype(str) + '-' + calendar_data['week'].astype(str).str.zfill(2)
    
    heatmap_data = calendar_data.pivot_table(index='weekday', columns='year_week', values='completed', fill_value=0).sort_index(axis=1)

    # Simplified color map: one for 'no completion', one for 'completion'
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
    ax.set_title("Daily Task Completion Status", fontsize=16, pad=20)
    plt.tight_layout()
    return fig

def display_task_list(tasks):
    """Displays a simple, non-interactive list of tasks and their status."""
    st.header("Task Status Overview")
    
    sorted_tasks = sorted(tasks, key=lambda x: x['date'], reverse=True)

    for task in sorted_tasks:
        if task['status'] == 'completed':
            icon = "✅"
            text = f"~~{task['task']}~~"
        else:
            icon = "⏳"
            text = task['task']
            
        st.markdown(f"{icon} {text} <span style='color:grey; font-size: smaller;'>*(Due {task['date'].strftime('%Y-%m-%d')})*</span>", unsafe_allow_html=True)


# --- Main App UI ---
st.title("Task Completion Visualizer 🟢")
st.write("This dashboard shows the status of a predefined set of tasks. The calendar is green on days with at least one completed task.")

tasks = get_static_tasks()

st.markdown("---")
st.pyplot(create_completion_heatmap(tasks))
st.markdown("---")
display_task_list(tasks)
