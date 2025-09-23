LeetCode-Style Task Tracker ✅

A personal task and habit tracker built with Python and Streamlit, inspired by the GitHub contribution graph. It uses a permanent Firebase Firestore cloud database to sync your data across all devices.

✨ Key Features
☁️ Cloud Sync: Data is saved permanently in a secure Firebase database.

🗓️ Activity Heatmap: A calendar heatmap visualizes your daily productivity.

⚡ Streak Tracking: Monitors your current and maximum consecutive day streaks.

📝 Task Management: A simple UI to add, complete, filter, and delete tasks.

🛠️ Tech Stack
Framework: Streamlit

Language: Python

Database: Google Firebase Firestore

Libraries: pandas, matplotlib, seaborn, google-cloud-firestore

🚀 Quick Start & Deployment Guide
1. Set Up a Free Firebase Database
In the Firebase Console, create a new project and a Firestore Database.

Start in production mode.

In the Rules tab, replace the default rule with allow read, write: if request.auth != null; and publish.

In Project settings > Service accounts, click "Generate new private key" to download your secret JSON file.

2. Deploy to Streamlit Community Cloud
Upload the project files (app.py, requirements.txt) to a new public GitHub repository.

On Streamlit Community Cloud, create a "New app" and select your repository.

In Advanced settings > Secrets, paste the contents of your downloaded JSON file using the following format:

textkey = '''
PASTE_YOUR_ENTIRE_JSON_CONTENT_HERE
'''

Click "Deploy!".

💻 How to Run Locally
1.Install libraries:

2.pip install -r requirements.txt

3.Create a local secrets file:

4.Create a folder named .streamlit in your project directory.

5.Inside it, create a file named secrets.toml.

6.Paste your secret key into this file using the same format as in the deployment guide.

7.Run the app:

      streamlit run app.py
