# LinkedIn Manager Tool

A cross-platform tool for LinkedIn automation, community engagement, and profile analysis using Flask and SQLite.

## Features
- **Dashboard**: Track your post and quiz activity.
- **Post Generator**: simple AI-powered interface to generate LinkedIn content.
- **Quiz System**: Gamified learning with a leaderboard.
- **Account Review**: Mock AI analysis of your profile.

## Setup & Run

### 1. Install Dependencies
Make sure you have Python 3 installed. Then install the required libraries:

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment (Optional)
If you have an OpenAI API Key for the generic post generation, set it as an environment variable. If not, the app will run in "Mock Mode" for testing.

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-..."
```

**Windows (CMD):**
```cmd
set OPENAI_API_KEY=sk-...
```

### 3. Run the Application
Start the Flask server:

```bash
python app.py
```

### 4. Open in Browser
Visit [http://localhost:3000](http://localhost:3000)

## Project Structure
- `app.py`: Main Flask application.
- `instance/database.db`: SQLite database (auto-created on first run).
- `templates/`: HTML files using Bootstrap 5.
- `static/`: CSS and assets.
