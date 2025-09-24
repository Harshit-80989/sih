import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap
import random

# --- CONFIGURATION ---
st.set_page_config(page_title="Data Science Journey", page_icon="🎓", layout="wide")


# --- STATIC DATA GENERATION (Replaces Database) ---
# This function creates a sample list of completed data science tasks.
def get_journey_data():
    """Generates a hardcoded list of tasks for the 'Learnt DATA SCIENCE' goal."""
    tasks = []
    today = datetime.date.today()
    
    # List of possible sub-tasks with days ago they might have been completed
    learning_path = [
        ("Setup Python & Dev Environment", 300), ("Completed Python Basics Course", 290),
        ("Learned NumPy for numerical data", 270), ("Mastered Pandas for data manipulation", 260),
        ("Practiced data cleaning on a messy dataset", 255), ("Web Scraped data with BeautifulSoup", 240),
        ("Learned Matplotlib for plotting", 230), ("Created advanced charts with Seaborn", 225),
        ("Understood Statistical Concepts (Mean, Median, Variance)", 210),
        ("Completed a course on Probability", 200), ("Learned Linear Regression", 180),
        ("Built a Logistic Regression model", 175), ("Studied Decision Trees and Random Forests", 160),
        ("Completed an NLP project with NLTK", 140), ("Fine-tuned a Hugging Face Transformer model", 130),
        ("Understood SQL and relational databases", 110), ("Practiced complex SQL queries", 105),
        ("Deployed a model using Flask API", 70), ("Containerized an app with Docker", 65),
        ("Built an interactive dashboard with Streamlit", 40), ("Completed a Kaggle competition", 30),
        ("Finalized my Data Science portfolio", 10), ("Reviewed project and updated resume", 5)
    ]

    for i, (task_desc, days_ago) in enumerate(learning_path):
        task_date = today - timedelta(days=days_ago)
        tasks.append({
            'id': f'task_{i}',
            'date': datetime.datetime.combine(task_date, datetime.datetime.min.time()),
            'task': task_desc,
            'status': 'completed'
        })
    
    # Add some random "practice" days to make the heatmap look more realistic
    for _ in range(40):
        random_date = today - timedelta(days=random.randint(10, 300))
        tasks.append({
            'id': f'practice_{_}',
            'date': datetime.datetime.combine(random_date, datetime.datetime.min.time()),
            'task': 'Daily practice & problem solving',
            'status': 'completed'
        })
        
    return tasks


# --- CORE LOGIC & PLOTTING (Largely Unchanged) ---

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
    if not tasks:
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.text(0.5, 0.5, 'No activity to display', ha='center', va='center')
        return fig

    df = pd.DataFrame(tasks)
    df['date'] = pd.to_datetime(df['date'])
    daily_counts = df.groupby(df['date'].dt.date).size()
    
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
    ax.set_title("Learning Contributions (Last Year)", fontsize=16, pad=20)
    plt.tight_layout()
    return fig

def display_task_list(tasks):
    """Displays a simple, non-interactive list of completed tasks."""
    st.header("Key Milestones Achieved")
    
    sorted_tasks = sorted(tasks, key=lambda x: x['date'], reverse=True)

    for task in sorted_tasks:
        # We display the task as completed (strikethrough)
        task_html = f"~~{task['task']}~~"
        st.markdown(f"✅ {task_html} <span style='color:grey; font-size: smaller;'>*(on {task['date'].strftime('%Y-%m-%d')})*</span>", unsafe_allow_html=True)
    st.balloons()


# --- Main App UI & Logic ---

# --- Sidebar (Simplified) ---
st.sidebar.header("Goal ✅")
st.sidebar.success("Learnt DATA SCIENCE")
st.sidebar.info("This dashboard visualizes the journey and milestones achieved towards completing the goal.")

# --- Main Page Display ---
st.title("My Data Science Learning Journey 🎓")
st.write("A visual record of the dedication and progress made to master Data Science.")

tasks = get_journey_data()

total_completed, tasks_last_week, total_active_days, max_streak, current_streak = calculate_stats(tasks)

st.header("Your Stats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Milestones Logged", f"{total_completed}", f"{tasks_last_week} in the last 7 days")
col2.metric("Total Active Learning Days", f"{total_active_days}")
col3.metric("Current Learning Streak", f"⚡ {current_streak} Days")
col4.metric("Max Learning Streak", f"🔥 {max_streak} Days")

st.markdown("---")
st.header("Activity Heatmap")
st.pyplot(create_calendar_heatmap(tasks))
st.markdown("---")

display_task_list(tasks)
