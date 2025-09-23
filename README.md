LeetCode-Style Task Tracker ✅
A personal task and habit tracker inspired by the LeetCode & GitHub contribution graph. This web application is built with Python and Streamlit, and it uses Google Firebase Firestore as a permanent cloud database, allowing your data to be saved and synced across all your devices.

✨ Key Features
☁️ Cloud Data Sync: All tasks are stored in a secure Firebase Firestore database. Your data is always up-to-date, whether you're on your laptop or phone.

🗓️ Contribution Heatmap: Visualize your productivity with a calendar heatmap that shows your activity over the last year. The more tasks you complete on a given day, the deeper the shade of green.

⚡ Streak Tracking: Stay motivated by tracking your Current Streak and Max Streak of consecutive active days.

📝 Full Task Management: Add, complete, filter, and delete tasks with a simple and intuitive user interface.

🚀 Deployable: Designed to be deployed for free on Streamlit Community Cloud.

🛠️ Tech Stack
Framework: Streamlit

Language: Python

Database: Google Firebase Firestore

Libraries:

pandas for data manipulation

matplotlib & seaborn for data visualization

google-cloud-firestore for database interaction

🚀 Setup and Deployment Guide
Follow these steps to deploy your own instance of this task tracker.

Prerequisites
A GitHub account.

A Google Cloud/Firebase account.

Step 1: Get the Code
Clone or fork this repository to your own GitHub account.

git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name

Step 2: Set Up the Firebase Database
This is where your app's data will be permanently stored.

Create a Firebase Project: Go to the Firebase Console, click "Add project", and give it a name.

Create a Firestore Database:

From your project's dashboard, go to Build > Firestore Database.

Click "Create database".

Select "Start in production mode" (important for security).

Choose a server location near you and click "Enable".

Set Security Rules:

In your new database, go to the "Rules" tab.

Delete the existing rules and replace them with the following, which allows only authenticated users (your app) to access the data:

rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}

Click "Publish".

Generate a Private Key:

Click the gear icon ⚙️ next to "Project Overview" and select "Project settings".

Go to the "Service accounts" tab.

Click "Generate new private key". A JSON file containing your secret credentials will download. Treat this file like a password.

Step 3: Deploy to Streamlit Community Cloud
Sign Up/In: Go to share.streamlit.io and log in with your GitHub account.

Create a New App:

Click "New app".

Select the GitHub repository you just set up.

Ensure the "Main file path" is app.py.

Add the Secret Key:

Before deploying, go to the "Advanced settings".

In the "Secrets" text box, paste the following, using triple quotes to avoid formatting errors:

textkey = '''
PASTE_THE_ENTIRE_CONTENTS_OF_YOUR_DOWNLOADED_JSON_FILE_HERE
'''

Open the JSON file you downloaded from Firebase, copy its entire contents, and paste it over the placeholder text.

Deploy!

Click "Deploy!". Streamlit will build your app and connect it to your database. In a few moments, your tracker will be live!

💻 How to Run Locally
To run the app on your own machine for development:

Install Libraries:

pip install -r requirements.txt

Create a Secrets File:

In your project directory, create a folder named .streamlit.

Inside .streamlit, create a file named secrets.toml.

Paste your secret key into secrets.toml using the same format as in Step 3 of the deployment guide.

Run the App:

streamlit run app.py

