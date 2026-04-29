from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import os
import openai
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import csv

# ------------------ CONFIG -------------------
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this for production!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------ MODELS -------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128)) # In a real app, store hashed passwords
    points = db.Column(db.Integer, default=0)
    badge = db.Column(db.String(50), default="Newbie")
    about = db.Column(db.Text, nullable=True) # For account review

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    post_type = db.Column(db.String(50))
    tone = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    option1 = db.Column(db.String(200))
    option2 = db.Column(db.String(200))
    option3 = db.Column(db.String(200))
    option4 = db.Column(db.String(200)) # Simple way to store options
    correct_option = db.Column(db.String(200)) # Store the correct answer string

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False) # 'Post', 'Quiz', 'Login'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class QuizResult(db.Model): # To track if a user took a quiz
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ HELPERS ------------------
def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# ------------------ ROUTES -------------------

@app.route('/')
def home():
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return render_template('index.html') # You might want a landing page or redirect to login

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        # Simple login for prototype: create user if not exists
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
            # Log activity
            act = Activity(user_id=user.id, action_type="Login")
            db.session.add(act)
            db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # Metrics
    total_posts = Post.query.filter_by(user_id=user.id).count()
    total_quizzes_taken = QuizResult.query.filter_by(user_id=user.id).count()
    
    # Recent Activity
    activities = Activity.query.filter_by(user_id=user.id).order_by(Activity.timestamp.desc()).limit(10).all()
    
    # Chart Data (simplified for last 10 activities)
    chart_data = {
        "labels": [a.timestamp.strftime("%Y-%m-%d") for a in activities],
        "post_counts": [1 if a.action_type=="Post" else 0 for a in activities],
        "quiz_counts": [1 if a.action_type=="Quiz" else 0 for a in activities]
    }

    return render_template('dashboard.html', username=user.username, metrics={
        "total_posts": total_posts,
        "total_quizzes_taken": total_quizzes_taken
    }, activities=activities, chart_data=chart_data)

@app.route('/post-generator', methods=['GET', 'POST'])
def post_generator():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    generated_post = ''
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.date.desc()).all()

    if request.method == 'POST':
        topic = request.form['topic']
        post_type = request.form['post_type']
        tone = request.form['tone']

        prompt = f"Generate a LinkedIn {post_type} post with a {tone} tone about: {topic}"
        try:
            # Mocking OpenAI if no key is present for dev purposes
            if not openai.api_key:
                 generated_post = f"[MOCK AI OUTPUT] Here is a {tone} {post_type} post about {topic}.\n\n#LinkedIn #{topic.replace(' ', '')}"
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200
                )
                generated_post = response.choices[0].message.content.strip()
        except Exception as e:
            generated_post = f"Error: {str(e)}"

        # Save to DB
        new_post = Post(user_id=user.id, topic=topic, post_type=post_type, tone=tone, content=generated_post)
        db.session.add(new_post)
        
        # Log Activity
        act = Activity(user_id=user.id, action_type="Post")
        db.session.add(act)
        
        db.session.commit()
        posts = Post.query.filter_by(user_id=user.id).order_by(Post.date.desc()).all() # Refresh list

    return render_template('post_generator.html', username=user.username, generated_post=generated_post, posts=posts)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    quizzes = Quiz.query.all()
    score = None
    user_answers = {}

    if request.method == 'POST':
        correct_count = 0
        for q in quizzes:
            ans = request.form.get(str(q.id))
            user_answers[str(q.id)] = ans
            if ans == q.correct_option:
                correct_count += 1
        
        score = correct_count
        
        # Save Result
        res = QuizResult(user_id=user.id, score=score)
        db.session.add(res)
        
        # Update User Points 
        user.points += (score * 10) # 10 points per correct answer
        
        # Log Activity
        act = Activity(user_id=user.id, action_type="Quiz")
        db.session.add(act)
        
        db.session.commit()

    return render_template('quiz.html', username=user.username, quizzes=quizzes, score=score, user_answers=user_answers)

@app.route('/account-review', methods=['GET', 'POST'])
def account_review():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    analysis = ""
    if request.method == 'POST':
        # In a real app, this would fetch data from LinkedIn API
        # Here we verify the logic idea: analyze user input or stored profile
        profile_text = user.about if user.about else "Generic tech lead profile."
        
        prompt = f"Identify 3 strengths and 3 weaknesses of this profile for a Tech Lead role: {profile_text}"
        
        try:
             if not openai.api_key:
                 analysis = "1. Strength: Leadership \n2. Strength: Python Skills\n3. Weakness: Needs more frequent posting."
             else:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300
                )
                analysis = response.choices[0].message.content.strip()
        except Exception as e:
            analysis = f"Error: {str(e)}"

    return render_template('account_review.html', analysis=analysis)

@app.route('/leaderboard')
def leaderboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Get top 5 users by points
    top_users = User.query.order_by(User.points.desc()).limit(5).all()
    
    return render_template('leaderboard.html', username=user.username, top_users=top_users)

@app.route('/init-db')
def init_db():
    db.create_all()
    # Add dummy quiz data if empty
    if not Quiz.query.first():
        q1 = Quiz(question="What is the best time to post on LinkedIn?", option1="9am", option2="10pm", option3="2am", option4="Anytime", correct_option="9am")
        q2 = Quiz(question="What is a good engagement rate?", option1="0.1%", option2="2%", option3="50%", option4="100%", correct_option="2%")
        db.session.add(q1)
        db.session.add(q2)
        db.session.commit()
    return "Database initialized!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ensure tables exist
    app.run(host='0.0.0.0', port=3000, debug=True)

