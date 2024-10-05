
"""
Your major problem is session_id when you  try to update goal with respect to session_id then error is occured
and also problem occured in delete_child method when you delete the child then child itself delete but session_id 
    
    """

import os
import uuid
import json
import logging
import tempfile
import requests
import csv
import io
import time
from io import StringIO, BytesIO
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Flask and extensions
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session as FlaskSession
from werkzeug.security import generate_password_hash, check_password_hash

# Third-party libraries
from redis import Redis
from deep_translator import GoogleTranslator
from langdetect import detect
import pandas as pd
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Google-related imports
from google.cloud import dialogflow_v2 as dialogflow
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.auth.exceptions import RefreshError

# Data visualization
import openpyxl
from openpyxl import Workbook
from openpyxl.chart import PieChart, LineChart, Reference
from openpyxl.drawing.image import Image
import matplotlib.pyplot as plt

# Ensure you're using the correct session object
from flask import session as flask_session
 
# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace("postgres://", "postgresql://", 1)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = Redis.from_url(os.getenv('REDIS_URL'))
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure cookies are only sent over HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
    
# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
sess = FlaskSession(app)

# Initialize session with the app
sess.init_app(app)



# ---------------------------
# Database Models and Routes
# ---------------------------

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    progress = db.Column(db.JSON, nullable=True)
    session_id = db.Column(db.String(36), nullable=True)  # Session ID for tracking purposes

# User Information model
class UserInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    surname = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Children model
class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    surname = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    father_name = db.Column(db.String(150), nullable=True)
    mother_name = db.Column(db.String(150), nullable=True)
    contact_phone_number = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Session Details model
class SessionDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    therapy_type = db.Column(db.String(150), nullable=False)
    session_date = db.Column(db.DateTime, nullable=False)
   
    goals = db.relationship('Goal', backref='session', lazy=True)

# Goal model
class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session_detail.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    goal_id = db.Column(db.String(50), unique=True)
    progress_update = db.Column(db.Text, nullable=True)
    activities_performed = db.Column(db.Text, nullable=True)
    notes_comments = db.Column(db.Text, nullable=True)
    def __init__(self, *args, **kwargs):
        super(Goal, self).__init__(*args, **kwargs)
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())

class SessionMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flask_session_id = db.Column(db.String(36), nullable=False)
    dialogflow_session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

def clean_up_old_mappings():
    expiry_duration = timedelta(days=30)  # Set your desired expiry duration
    expiry_date = datetime.now(timezone.utc) - expiry_duration
    SessionMapping.query.filter(SessionMapping.created_at < expiry_date).delete()
    db.session.commit()

@app.before_first_request
def create_tables():
    db.create_all()

#def perform_database_backup():
    # Add code to backup your database
 #   print("Performing database backup...")

#scheduler = BackgroundScheduler()
#scheduler.add_job(func=clean_up_old_mappings, trigger="interval", days=1)
#scheduler.add_job(func=perform_database_backup, trigger="interval", weeks=1)
#scheduler.start()

##atexit.register(lambda: scheduler.shutdown())


@app.route('/googlec799203314e18a4a.html')
def google_verification():
    return send_from_directory('static', 'googlec799203314e18a4a.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user:
            error = 'Username already exists'
            return render_template('register.html', error=error)

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user is None:
            error = 'Incorrect username' 
            logging.debug(error)
            return render_template('login.html', error=error)
        elif not check_password_hash(user.password, password):
            error = 'Incorrect password'
            logging.debug(error)
            return render_template('login.html', error=error)
        else:
            session['user_id'] = user.id
            if user.session_id:
                session['session_id'] = user.session_id
            else:
                session['session_id'] = str(uuid.uuid4())
                user.session_id = session['session_id']
                logging.debug(f"New session ID generated: {user.session_id}")
                db.session.commit()

            return redirect(url_for('home'))

    logging.debug("Rendering login page")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('session_id', None)
    return redirect(url_for('login'))

@app.route('/update_progress', methods=['POST'])
def update_progress():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return 'User not found', 404
    
    # Get progress data from the request
    progress_data = request.json.get('progress_data')
    
    if not progress_data:
        return 'No progress data are present', 400
    
    # Update the user's progress
    user.progress = progress_data
    db.session.commit()
    
    return jsonify({'message': 'Progress updated successed'}), 200
@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/stories_games')
def stories_games():
    return render_template('stories_games.html')

@app.route('/index')
def index():
    return render_template('index.html')

# Manage Profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    if request.method == 'POST':
        first_name = request.form['first_name']
        surname = request.form['surname']
        phone_number = request.form['phone_number']
        gender = request.form['gender']
        role = request.form['role']
        
        user_info = UserInfo.query.filter_by(user_id=user_id).first()
        if user_info:
            # Update existing user information
            user_info.first_name = first_name
            user_info.surname = surname
            user_info.phone_number = phone_number
            user_info.gender = gender
            user_info.role = role
        else:
            # Create new user information
            user_info = UserInfo(
                first_name=first_name, surname=surname, phone_number=phone_number, 
                gender=gender, role=role, user_id=user_id)
            db.session.add(user_info)
        
        db.session.commit()
    
    user_info = UserInfo.query.filter_by(user_id=user_id).first()
    return render_template('profile.html', user_info=user_info)

@app.route('/children_progress', methods=['GET', 'POST'])
def children_progress():
    app.logger.debug(f"Session data: {flask_session}")

    
    user_id = session['user_id']
    children = Child.query.filter_by(user_id=user_id).all()
    
    if request.method == 'POST':
        if 'add_child' in request.form:
            first_name = request.form['first_name']
            surname = request.form['surname']
            gender = request.form['gender']
            father_name = request.form.get('father_name')
            mother_name = request.form.get('mother_name')
            contact_phone_number = request.form.get('contact_phone_number')
            
            new_child = Child(
                first_name=first_name, surname=surname, gender=gender, 
                father_name=father_name, mother_name=mother_name, 
                contact_phone_number=contact_phone_number, user_id=user_id)
            db.session.add(new_child)
            db.session.commit()
            return redirect(url_for('children_progress'))
        
        elif 'update_child' in request.form:
            print(f"Received request to update child with ID: {child_id}")

            child_id = request.form['child_id']
            print("Updating child ID:", child_id)

            child = Child.query.get(child_id)
            if not child:
                print(f"Child with ID {child_id} not found")

                return 'Child not found', 404
            print("Request form data:", request.form)

            child.first_name = request.form['first_name']
            child.surname = request.form['surname']
            child.gender = request.form['gender']
            child.father_name = request.form.get('father_name')
            child.mother_name = request.form.get('mother_name')
            child.contact_phone_number = request.form.get('contact_phone_number')
            
            db.session.commit()
            print(f"Child with ID {child_id} updated successfully")

            return redirect(url_for('children_progress'))
        
        elif 'delete_child' in request.form:
            child_id = request.form['child_id']
            child = Child.query.get(child_id)
            if not child:
                return 'Child not found', 404
            
            db.session.delete(child)
            db.session.commit()
            return redirect(url_for('children_progress'))
    
    return render_template('children_progress.html', children=children)

@app.route('/add_child', methods=['POST'])
def add_child():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    first_name = request.form['first_name']
    surname = request.form['surname']
    gender = request.form['gender']
    father_name = request.form.get('father_name')
    mother_name = request.form.get('mother_name')
    contact_phone_number = request.form.get('contact_phone_number')
    
    new_child = Child(
        first_name=first_name, surname=surname, gender=gender, 
        father_name=father_name, mother_name=mother_name, 
        contact_phone_number=contact_phone_number, user_id=user_id)
    db.session.add(new_child)
    db.session.commit()
    
    return redirect(url_for('children_progress'))

@app.route('/update_child/<int:id>', methods=['POST'])
def update_child(id):
    logging.info(f"Received request to update child with ID: {id}")
    
    child = Child.query.get(id)
    if not child:
        logging.error(f"Child with ID {id} not found.")
        return 'Child not found', 404
    
    try:
        logging.info(f"Updating child ID: {id}")
        logging.debug(f"Request form data: {request.form}")
        
        # Validate and update child fields
        child.surname = request.form['surname']
        child.gender = request.form['gender']
        child.father_name = request.form['father_name']
        child.mother_name = request.form['mother_name']
        child.contact_phone_number = request.form['contact_phone_number']
        
        db.session.commit()
        logging.info(f"Child ID {id} successfully updated.")
        return redirect(url_for('children_progress'))
    except KeyError as e:
        logging.error(f"Missing form field: {e}")
        return 'Bad request: Missing form field', 400
    except Exception as e:
        logging.error(f"Error updating child: {e}")
        return 'Error updating child', 500



@app.route('/delete_child/<int:child_id>', methods=['POST'])

def delete_child(child_id):
    
    child = Child.query.get(child_id)
    if not child:
        return 'Child not found', 404
    
    db.session.delete(child)
    db.session.commit()
    return redirect(url_for('children_progress'))


@app.route('/child/<int:child_id>/sessions', methods=['GET', 'POST'])
def child_sessions(child_id):
    if 'user_id' not in flask_session:
        return redirect(url_for('login'))

    user_id = flask_session['user_id']
    user_info = UserInfo.query.filter_by(user_id=user_id).first()
 # Map user roles to therapy types
    role_to_therapy = {
        'EmotionalTherapist': 'Emotional Therapist',
        'OccupationalTherapist': 'Occupational Therapist',
        'PhysioTherapist': 'Physiotherapist',
        'SpeechTherapist': 'Speech Therapist'
    }

    # Get the default therapy type based on user's role
    default_therapy_type = role_to_therapy.get(user_info.role, 'Unknown') if user_info else 'Unknown'
    child = Child.query.get(child_id)
    if not child:
        logging.error(f"Child with ID {child_id} not found.")
        return 'Child not found', 404
    
    sessions = SessionDetail.query.filter_by(child_id=child_id).order_by(SessionDetail.session_date).all()
    
    chart_data = []
    for session in sessions:
        session_data = {
            'date': session.session_date.strftime('%Y-%m-%d'),
            'goals': [{'description': goal.description, 'rating': goal.rating} for goal in session.goals]
        }
        chart_data.append(session_data)
    
    return render_template('sessions.html', child=child, sessions=sessions, chart_data=json.dumps(chart_data), datetime=datetime, user_info=user_info, default_therapy_type=default_therapy_type)
@app.route('/child/<int:child_id>/add_session', methods=['POST'])
def add_session(child_id):
    try:
        app.logger.info(f"Received form data: {request.form.to_dict()}")


        user_id = session['user_id']
        user_info = UserInfo.query.filter_by(user_id=user_id).first()

        # Map user roles to therapy types
        role_to_therapy = {
            'EmotionalTherapist': 'Emotional Therapist',
            'OccupationalTherapist': 'Occupational Therapist',
            'PhysioTherapist': 'Physiotherapist',
            'SpeechTherapist': 'Speech Therapist'
        }

        # Use the user's role to set the therapy type
        therapy_type = role_to_therapy.get(user_info.role, 'Unknown')
        session_date = datetime.strptime(request.form['session_date'], '%Y-%m-%dT%H:%M')

        setting_goals = []
        progress_ratings = []
        progress_updates = []
        activities_performed = []
        notes_comments = []

        for key, value in request.form.items():
            if key.startswith('setting_goals['):
                setting_goals.append(value)
            elif key.startswith('progress_rating['):
                progress_ratings.append(value)
            elif key.startswith('progress_update['):
                progress_updates.append(value)
            elif key.startswith('activities_performed['):
                activities_performed.append(value)
            elif key.startswith('notes_comments['):
                notes_comments.append(value)

        app.logger.info(f"Extracted goals: {setting_goals}")
        app.logger.info(f"Extracted ratings: {progress_ratings}")
        app.logger.info(f"Extracted progress updates: {progress_updates}")
        app.logger.info(f"Extracted activities performed: {activities_performed}")
        app.logger.info(f"Extracted notes/comments: {notes_comments}")

        if not setting_goals or not progress_ratings or len(setting_goals) != len(progress_ratings):
            app.logger.error(f"Goals and ratings mismatch. Goals: {setting_goals}, Ratings: {progress_ratings}")
            return jsonify({"success": False, "message": "Goals and ratings must be provided and match in number."}), 400

        new_session = SessionDetail(
            child_id=child_id, therapy_type=therapy_type, session_date=session_date)

        db.session.add(new_session)
        db.session.flush()

        for i, (goal, rating) in enumerate(zip(setting_goals, progress_ratings)):
            if goal.strip() and rating:
                new_goal = Goal(
                    session_id=new_session.id,
                    description=goal.strip(),
                    rating=int(rating),
                    progress_update=progress_updates[i] if i < len(progress_updates) else '',
                    activities_performed=activities_performed[i] if i < len(activities_performed) else '',
                    notes_comments=notes_comments[i] if i < len(notes_comments) else ''
                )
                db.session.add(new_goal)

        db.session.commit()
        app.logger.info(f"Session added successfully for child {child_id} with {len(setting_goals)} goals")
        return jsonify({"success": True, "message": "Session added successfully."})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding session: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_session/<int:session_id>', methods=['POST'])
def update_session(session_id):
    session_detail = SessionDetail.query.get(session_id)
    if not session_detail:
        return jsonify({"success": False, "message": "Session not found"}), 404

    try:
        app.logger.info(f"Received form data: {request.form.to_dict()}")
        user_id = session['user_id']
        user_info = UserInfo.query.filter_by(user_id=user_id).first()

        # Map user roles to therapy types
        role_to_therapy = {
            'EmotionalTherapist': 'Emotional Therapist',
            'OccupationalTherapist': 'Occupational Therapist',
            'PhysioTherapist': 'Physiotherapist',
            'SpeechTherapist': 'Speech Therapist'
        }

        # Use the user's role to set the therapy type
        therapy_type = role_to_therapy.get(user_info.role, 'Unknown')

        session_detail.therapy_type = therapy_type
        session_detail.session_date = datetime.strptime(request.form['session_date'], '%Y-%m-%dT%H:%M')
        
        # Delete existing goals
        Goal.query.filter_by(session_id=session_id).delete()

        # Add new goals
        setting_goals = []
        progress_ratings = []
        progress_updates = []
        activities_performed = []
        notes_comments = []

        for key, value in request.form.items():
            if key.startswith('setting_goals['):
                setting_goals.append(value)
            elif key.startswith('progress_rating['):
                progress_ratings.append(value)
            elif key.startswith('progress_update['):
                progress_updates.append(value)
            elif key.startswith('activities_performed['):
                activities_performed.append(value)
            elif key.startswith('notes_comments['):
                notes_comments.append(value)

        app.logger.info(f"Extracted goals: {setting_goals}")
        app.logger.info(f"Extracted ratings: {progress_ratings}")
        app.logger.info(f"Extracted progress updates: {progress_updates}")
        app.logger.info(f"Extracted activities performed: {activities_performed}")
        app.logger.info(f"Extracted notes/comments: {notes_comments}")

        # Ensure we have the same number of goals and ratings
        min_length = min(len(setting_goals), len(progress_ratings))
        setting_goals = setting_goals[:min_length]
        progress_ratings = progress_ratings[:min_length]
        
        if not setting_goals or not progress_ratings or len(setting_goals) != len(progress_ratings):
            app.logger.error(f"Goals and ratings mismatch. Goals: {setting_goals}, Ratings: {progress_ratings}")
            return jsonify({"success": False, "message": "Goals and ratings must be provided and match in number."}), 400

        # Remove duplicates while preserving order
        goals_and_ratings = list(dict.fromkeys(zip(setting_goals, progress_ratings)))

        for i, (goal, rating) in enumerate(goals_and_ratings):
            if goal.strip() and rating:
                new_goal = Goal(
                    session_id=session_id,
                    description=goal.strip(),
                    rating=int(rating),
                    progress_update=progress_updates[i] if i < len(progress_updates) else '',
                    activities_performed=activities_performed[i] if i < len(activities_performed) else '',
                    notes_comments=notes_comments[i] if i < len(notes_comments) else ''
                )
                db.session.add(new_goal)

        db.session.commit()
        app.logger.info(f"Session ID {session_id} successfully updated with {len(goals_and_ratings)} goals.")
        return jsonify({"success": True, "message": f"Session ID {session_id} successfully updated with {len(goals_and_ratings)} goals."})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating session {session_id}: {str(e)}")
        return jsonify({"success": False, "message": f"Error updating session: {str(e)}"}), 500

@app.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    session_detail = SessionDetail.query.get(session_id)
    if not session_detail:
        app.logger.error(f"Session with ID {session_id} not found.")
        return jsonify({"success": False, "message": "Session not found"}), 404

    try:
        child_id = session_detail.child_id
        Goal.query.filter_by(session_id=session_id).delete()  # Delete associated goals
        db.session.delete(session_detail)
        db.session.commit()
        
        app.logger.info(f"Deleted session ID {session_id} and associated goals.")
        return jsonify({"success": True, "message": f"Session ID {session_id} and associated goals deleted successfully."})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting session ID {session_id}: {e}")
        return jsonify({"success": False, "message": f"Error deleting session: {str(e)}"}), 500
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.container.ui'
]

def create_flow():
    client_config = json.loads(os.getenv('GOOGLE_OAUTH_CLIENT_CONFIG'))
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
# OAuth routes
@app.route('/authorize')
def authorize():
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    flask_session['state'] = state
    return redirect(authorization_url)


def check_required_scopes(credentials):
    required_scopes = set(SCOPES)
    current_scopes = set(credentials.scopes)
    missing_scopes = required_scopes - current_scopes
    if missing_scopes:
        app.logger.error(f"Missing scopes: {missing_scopes}")
        return False
    return True


@app.route('/oauth2callback')
def oauth2callback():
    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)
    
    credentials = flow.credentials
    app.logger.info(f"Received scopes immediately after authorization: {credentials.scopes}")
    
    flask_session['credentials'] = credentials_to_dict(credentials)
    
    return redirect(url_for('children_progress', oauth_success='true'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
@app.route('/reauthorize')
def reauthorize():
    flask_session.clear()
    return redirect(url_for('authorize'))


def create_apps_script(credentials, SPREADSHEET_ID):
    script_content_part1 = '''
// Google Apps Script Code

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Custom Menu')
    .addItem('Generate Reports', 'showSidebar')
    .addToUi();
}

function showSidebar() {
  var html = HtmlService.createHtmlOutput('<button onclick="google.script.run.generateReports()">Generate Reports</button>')
      .setTitle('Generate Reports')
      .setWidth(300);
  SpreadsheetApp.getUi().showSidebar(html);
}

function doGet(e) {
  return HtmlService.createHtmlOutput('<button onclick="google.script.run.generateReports()">Generate Reports</button>');
}

function generateReports() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var rawDataSheet = ss.getSheetByName('Raw Data'); // Updated sheet name
  var individualReportsSheet = ss.getSheetByName('Individual Reports');
  
  if (!individualReportsSheet) {
    SpreadsheetApp.getUi().alert('Creating Individual Reports sheet.');
    individualReportsSheet = ss.insertSheet('Individual Reports');
  }
  
  // Clear existing data and charts
  individualReportsSheet.clear();

  var data = rawDataSheet.getDataRange().getValues();
  var headers = data.shift();
  
  // Group data by child
  var childrenData = {};
  data.forEach(function(row) {
    var childName = row[0];
    if (!childrenData[childName]) {
      childrenData[childName] = [];
    }
    childrenData[childName].push(row);
  });
  
  // Generate individual reports
  generateIndividualReports(individualReportsSheet, childrenData);
  
  Logger.log('Reports generated successfully!');
  return 'Reports generated successfully!';
}

function generateIndividualReports(sheet, childrenData) {
  sheet.clear();
  var maxRows = sheet.getMaxRows();
  var maxCols = sheet.getMaxColumns();
  var row = 1;
  var pageHeight = 60; // Reduced page height for less spacing between reports
  var childIndex = 0;
  var totalChildren = Object.keys(childrenData).length;
  
  for (var childName in childrenData) {
    childIndex++;
    var childData = childrenData[childName];
    
    // Ensure we have enough rows
    if (row + pageHeight > maxRows) {
      sheet.insertRowsAfter(maxRows, pageHeight);
      maxRows = sheet.getMaxRows();
    }
    
    // Set consistent row height
    sheet.setRowHeights(row, pageHeight, 21);
    
    // Add child name and page number
    sheet.getRange(row, 1).setValue('Report for ' + childName);
    sheet.getRange(row, 8).setValue('Page ' + childIndex + ' of ' + totalChildren);
    sheet.getRange(row, 1, 1, 8).setFontWeight('bold');
    row += 2; // Reduced spacing
    
    // Add goal summary
    sheet.getRange(row, 1).setValue('Goal Summary');
    sheet.getRange(row, 1, 1, 6).setFontWeight('bold');
    row += 1; // Reduced spacing
    sheet.getRange(row, 1).setValue('Goal');
    sheet.getRange(row, 2).setValue('Start Date');
    sheet.getRange(row, 3).setValue('End Date');
    sheet.getRange(row, 4).setValue('Initial Rating');
    sheet.getRange(row, 5).setValue('Final Rating');
    sheet.getRange(row, 6).setValue('Progress');
    sheet.getRange(row, 1, 1, 6).setFontStyle('italic');
    
    var goals = getGoals(childData);
    row++;
    goals.forEach(function(goal) {
      sheet.getRange(row, 1).setValue(goal.description);
      sheet.getRange(row, 2).setValue(goal.startDate);
      sheet.getRange(row, 3).setValue(goal.endDate);
      sheet.getRange(row, 4).setValue(goal.initialRating);
      sheet.getRange(row, 5).setValue(goal.finalRating);
      sheet.getRange(row, 6).setValue(goal.finalRating - goal.initialRating);
      row++;
    });
    
    // Add progress updates
    row += 2; // Reduced spacing
    sheet.getRange(row, 1).setValue('Progress Updates');
    sheet.getRange(row, 1, 1, 6).setFontWeight('bold');
    row += 1; // Reduced spacing
    sheet.getRange(row, 1).setValue('Date');
    sheet.getRange(row, 2).setValue('Goal');
    sheet.getRange(row, 3).setValue('Rating');
    sheet.getRange(row, 4).setValue('Progress Update');
    sheet.getRange(row, 5).setValue('Activities Performed');
    sheet.getRange(row, 6).setValue('Notes/Comments');
    sheet.getRange(row, 1, 1, 6).setFontStyle('italic');
    
    row++;
    var progressUpdates = getProgressUpdates(childData);
    progressUpdates.forEach(function(update) {
      if (row >= maxRows) {
        sheet.insertRowsAfter(maxRows, 1);
        maxRows++;
      }
      sheet.getRange(row, 1).setValue(update.date);
      sheet.getRange(row, 2).setValue(update.goal);
      sheet.getRange(row, 3).setValue(update.rating);
      sheet.getRange(row, 4).setValue(update.progressUpdate);
      sheet.getRange(row, 5).setValue(update.activitiesPerformed);
      sheet.getRange(row, 6).setValue(update.notes);
      row++;
    });
    
    // Add activities count table above the charts
    row = addActivitiesCountTable(sheet, childData, row + 2);
    
    // Add charts for this child
    row = addChildCharts(sheet, childData, row + 2);
    
    // Add page break for next child
    if (childIndex < totalChildren) {
      var remainingRows = pageHeight - (row % pageHeight);
      if (row + remainingRows > maxRows) {
        sheet.insertRowsAfter(maxRows, remainingRows);
        maxRows = sheet.getMaxRows();
      }
      sheet.setRowHeights(row, remainingRows, 21);
      row += remainingRows;
    }
  }
}

function addActivitiesCountTable(sheet, childData, startRow) {
  var activities = getActivityCounts(childData);
  var tableData = [['Activity', 'Count']];
  for (var activity in activities) {
    tableData.push([activity, activities[activity]]);
  }
  
  var tableRange = sheet.getRange(startRow, 1, tableData.length, 2);
  safelySetValues(tableRange, tableData);
  
  // Format the table
  sheet.getRange(startRow, 1, 1, 2).setFontWeight('bold');
  sheet.getRange(startRow, 1, tableData.length, 2).setBorder(true, true, true, true, true, true);
  sheet.getRange(startRow, 1, tableData.length, 2).setHorizontalAlignment('center');
  
  return startRow + tableData.length + 1;
}

function addChildCharts(sheet, childData, startRow) {
  var maxRows = sheet.getMaxRows();
  var maxCols = sheet.getMaxColumns();

  // Activity distribution chart
  var activities = getActivityCounts(childData);
  var chartData = [['Activity', 'Count']];
  for (var activity in activities) {
    chartData.push([activity, activities[activity]]);
  }
  
  if (startRow + chartData.length > maxRows) {
    sheet.insertRowsAfter(maxRows, chartData.length);
    maxRows = sheet.getMaxRows();
  }
  
  var chartRange = sheet.getRange(startRow, 1, chartData.length, 2);
  safelySetValues(chartRange, chartData);
  
  var chartBuilder = sheet.newChart()
    .setChartType(Charts.ChartType.PIE)
    .setOption('title', 'Activity Distribution')
    .setOption('pieHole', 0.4)
    .setOption('width', 400)
    .setOption('height', 300)
    .setPosition(startRow, 1, 0, 0);
  
  chartBuilder.addRange(chartRange);
  sheet.insertChart(chartBuilder.build());
  
  // Progress chart
  var goals = getGoals(childData);
  var progressUpdates = getProgressUpdates(childData);
  
  var progressMap = new Map();
  progressUpdates.forEach(function(update) {
    var dateString = update.date.toISOString().split('T')[0];
    if (!progressMap.has(dateString)) {
      progressMap.set(dateString, new Map());
    }
    progressMap.get(dateString).set(update.goal, update.rating);
  });
  
  var sortedDates = Array.from(progressMap.keys()).sort();
  var progressData = [['Date'].concat(goals.map(function(g) { return g.description; }))];
  sortedDates.forEach(function(dateString) {
    var dataRow = [new Date(dateString)];
    goals.forEach(function(goal) {
      var rating = progressMap.get(dateString).get(goal.description);
      dataRow.push(rating !== undefined ? rating : null);
    });
    progressData.push(dataRow);
  });
  
  if (startRow + progressData.length > maxRows) {
    sheet.insertRowsAfter(maxRows, progressData.length);
    maxRows = sheet.getMaxRows();
  }
  
  var progressRange = sheet.getRange(startRow, 5, progressData.length, progressData[0].length);
  safelySetValues(progressRange, progressData);
  
  var seriesObjects = goals.map(function(goal, index) {
    return {
      targetAxisIndex: 0,
      type: "line",
      color: getColorForIndex(index),
      labelInLegend: goal.description
    };
  });
  
  var progressChartBuilder = sheet.newChart()
    .setChartType(Charts.ChartType.LINE)
    .setOption('title', 'Goal Progress Over Time')
    .setOption('legend', {position: 'right', textStyle: {fontSize: 10}})
    .setOption('series', seriesObjects)
    .setOption('vAxis', {title: 'Rating', minValue: 0, maxValue: 10})
    .setOption('hAxis', {title: 'Date', format: 'yyyy-MM-dd'})
    .setOption('width', 500)
    .setOption('height', 300)
    .setPosition(startRow, 5, 0, 0);
  
  progressChartBuilder.addRange(progressRange);
  sheet.insertChart(progressChartBuilder.build());
  
  // Return the new row position after all charts
  return startRow + Math.max(chartData.length, progressData.length) + 2;
}

function getProgressUpdates(childData) {
  return childData.map(function(row) {
    return {
      date: new Date(row[2]),
      goal: row[3],
      rating: Number(row[4]),
      progressUpdate: row[5],
      activitiesPerformed: row[6],
      notes: row[7]
    };
  }).sort(function(a, b) {
    return a.date - b.date;
  });
}

function getGoals(childData) {
  var goals = {};
  childData.forEach(function(row) {
    var goalDescription = row[3];
    var date = new Date(row[2]);
    var rating = Number(row[4]);
    
    if (!goals[goalDescription]) {
      goals[goalDescription] = {
        description: goalDescription,
        startDate: date,
        endDate: date,
        initialRating: rating,
        finalRating: rating
      };
    } else {
      if (date < goals[goalDescription].startDate) {
        goals[goalDescription].startDate = date;
        goals[goalDescription].initialRating = rating;
      }
      if (date > goals[goalDescription].endDate) {
        goals[goalDescription].endDate = date;
        goals[goalDescription].finalRating = rating;
      }
    }
  });
  return Object.values(goals);
}

function getActivityCounts(childData) {
  var activities = {};
  childData.forEach(function(row) {
    var sessionActivities = row[6].split(',');
    sessionActivities.forEach(function(activity) {
      activity = activity.trim();
      activities[activity] = (activities[activity] || 0) + 1;
    });
  });
  return activities;
}

function safelySetValues(range, values) {
  if (!values || values.length === 0 || values[0].length === 0) {
    console.log('No data to set');
    return;
  }
  
  var numRows = Math.max(values.length, 1);
  var numCols = Math.max(values[0].length, 1);
  
  if (numRows > range.getNumRows() || numCols > range.getNumColumns()) {
    // Expand the range if necessary
    range = range.offset(0, 0, numRows, numCols);
  }
  range.setValues(values);
}

function getColorForIndex(index) {
  var colors = ['#3366cc', '#dc3912', '#ff9900', '#109618', '#990099', '#0099c6', '#dd4477', '#66aa00', '#b82e2e', '#316395'];
  return colors[index % colors.length];
}
    '''


    manifest_content = json.dumps({
        'timeZone': 'Asia/Jerusalem',
        'exceptionLogging': 'CLOUD'
    })

    try:
        # Create Apps Script project
        script_service = build('script', 'v1', credentials=credentials)
        script_project = {
            'title': 'Report Generator',
            'parentId': SPREADSHEET_ID
        }
        script_project = script_service.projects().create(body=script_project).execute()
        script_id = script_project['scriptId']

        # Add first part of the script
        request1 = {
            'files': [
                {
                    'name': 'Code',
                    'type': 'SERVER_JS',
                    'source': script_content_part1
                },
                {
                    'name': 'appsscript',
                    'type': 'JSON',
                    'source': manifest_content
                }
            ]
        }
        
        script_service.projects().updateContent(
            scriptId=script_id,
            body=request1
        ).execute()


        

        return "Apps Script created and attached successfully"
    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        error_message = error_details.get('error', {}).get('message', 'Unknown error')
        
        if "User has not enabled the Apps Script API" in error_message:
            app.logger.warning("Apps Script API not enabled")
            raise Exception("Apps Script API not enabled")
        elif "Syntax error" in error_message:
            # Extract line number from error message
            line_number = int(error_message.split('line:')[1].split()[0])
            
            # Determine which part of the script has the error
            if line_number <= script_content_part1.count('\n'):
                problematic_script = script_content_part1
                offset = 0
            script_lines = problematic_script.splitlines()
            start_line = max(0, line_number - offset - 6)
            end_line = min(len(script_lines), line_number - offset + 5)
            
            debug_info = f"Error on line {line_number}. Surrounding code:\n"
            for i in range(start_line, end_line):
                debug_info += f"{i+offset+1}: {script_lines[i]}\n"
            
            app.logger.error(f"Syntax error in Apps Script:\n{debug_info}")
            
            raise Exception(f"Syntax error in Apps Script: {error_message}\n{debug_info}")
        else:
            raise Exception(f'An error occurred while creating the Apps Script: {str(e)}')
    except Exception as e:
        app.logger.error(f"Unexpected error in create_apps_script: {str(e)}")
        raise

@app.route('/export_all_sessions', methods=['GET'])
def export_all_sessions():
    app.logger.info("Starting export process")
    if 'user_id' not in flask_session:
        app.logger.error("User not authenticated")
        return jsonify({'error': 'User not logged in'}), 401

    try:
        credentials = get_credentials()
        if not credentials:
            return jsonify({'error': 'No valid credentials', 'redirect': url_for('authorize')}), 401
        
        # Attempt to refresh the token if it's expired
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError:
                app.logger.error("Token refresh error")
                return jsonify({'error': 'Authentication expired', 'redirect': url_for('authorize')}), 401

        app.logger.info(f"Credentials scopes at the start of export_all_sessions: {credentials.scopes}")

        # Create Sheets API service
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        # Create a new spreadsheet
        spreadsheet = {
            'properties': {
                'title': f'Therapy Sessions Report - {datetime.now().strftime("%Y-%m-%d")}'
            }
        }
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        SPREADSHEET_ID = spreadsheet.get('spreadsheetId')
        app.logger.info(f"Created new spreadsheet with ID: {SPREADSHEET_ID}")

        # Rename the default sheet to "Raw Data"
        request = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": 0,  # ID of the first sheet
                                "title": "Raw Data"
                            },
                            "fields": "title"
                        }
                    }
                ]
            }
        )
        request.execute()
        app.logger.info("Renamed sheet to 'Raw Data'")

        # Prepare data
        user_id = flask_session['user_id']
        children = Child.query.filter_by(user_id=user_id).all()
        
        data = [['Child Name', 'Therapy Type', 'Session Date', 'Goals', 'Progress Rating', 'Progress Update', 'Activities Performed', 'Notes/Comments']]
        for child in children:
            sessions = SessionDetail.query.filter_by(child_id=child.id).order_by(SessionDetail.session_date).all()
            for session in sessions:
                for goal in session.goals:
                    data.append([
                        f"{child.first_name} {child.surname}",
                        session.therapy_type,
                        session.session_date.strftime('%Y-%m-%d %H:%M'),
                        goal.description,
                        goal.rating,
                        goal.progress_update,
                        goal.activities_performed,
                        goal.notes_comments
                    ])

        # Update the content of the spreadsheet
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='Raw Data!A1',
            valueInputOption='RAW',
            body={'values': data}
        ).execute()
        app.logger.info(f"Updated sheet: {result.get('updatedCells')} cells updated")
        app.logger.info(f"Scopes before Apps Script check: {credentials.scopes}")

        # Check if we have the necessary scope before creating the Apps Script project
        if 'https://www.googleapis.com/auth/script.projects' not in credentials.scopes:
            app.logger.error("Missing necessary scope for Apps Script API")
            return jsonify({'error': 'Missing necessary permissions. Please re-authorize the application.'}), 403

        try:
            # Use the create_apps_script function
            script_result = create_apps_script(credentials, SPREADSHEET_ID)
            app.logger.info(script_result)
        except Exception as e:
            if str(e) == "Apps Script API not enabled":
                error_message = "Please follow these steps:\n1. Visit the link below to open Google Script settings\n2. Enable the Apps Script API\n3. Wait a few minutes\n4. Try exporting again"
                app.logger.warning(f"Apps Script API not enabled: {error_message}")
                return jsonify({
                    'error': error_message,
                    'requires_api_enablement': True,
                    'link': "https://script.google.com/home/usersettings"
                }), 403
            else:
                raise  # Re-raise the exception if it's not the specific error we're looking for

        # Set the permissions to make the file accessible to anyone with the link
        drive_service = build('drive', 'v3', credentials=credentials)
        permission = {
            'type': 'anyone',
            'role': 'writer',
            'allowFileDiscovery': False
        }
        drive_service.permissions().create(
            fileId=SPREADSHEET_ID,
            body=permission,
            fields='id'
        ).execute()
        app.logger.info("Set spreadsheet permissions to public")

        spreadsheet_url = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=0'
        
        app.logger.info("Export completed successfully")
        return jsonify({
            'spreadsheetUrl': spreadsheet_url,
            'message': f'Data exported successfully. {result.get("updatedCells")} cells updated. ' +
                       'The spreadsheet is now accessible to anyone with the link. ' +
                       'A Google Apps Script has been added to generate a summary report.'
        })

    except HttpError as e:
        if e.resp.status == 403 and "User has not enabled the Apps Script API" in str(e):
            error_message = "Please follow these steps:\n1. Visit the link below to open Google Script settings\n2. Enable the Apps Script API\n3. Wait a few minutes\n4. Try exporting again"
            app.logger.warning(f"Apps Script API not enabled: {error_message}")
            return jsonify({
                'error': error_message,
                'requires_api_enablement': True,
                'link': "https://script.google.com/home/usersettings"
            }), 403
        else:
            app.logger.error(f"HTTP error in export_all_sessions: {str(e)}")
            return jsonify({'error': f'An error occurred while accessing Google services: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in export_all_sessions: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    

def get_credentials():
    if 'credentials' not in flask_session:
        app.logger.error("No credentials found in flask_session")
        return None
    
    credentials = Credentials(**flask_session['credentials'])
    
    app.logger.info(f"Current credential scopes: {credentials.scopes}")
    
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            flask_session['credentials'] = credentials_to_dict(credentials)
            app.logger.info(f"Refreshed credential scopes: {credentials.scopes}")
        except Exception as e:
            app.logger.error(f"Error refreshing credentials: {str(e)}")
            return None
    
    return credentials


@app.route('/clear_session')
def clear_session():
    flask_session.clear()
    return redirect(url_for('authorize'))
@app.route('/debug_scopes')
def debug_scopes():
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'No valid credentials'}), 401
    
    return jsonify({
        'scopes': credentials.scopes,
        'valid': credentials.valid,
        'expired': credentials.expired,
        'has_refresh_token': bool(credentials.refresh_token)
    })
# ---------------------------
# Bot Functionality
# ---------------------------
# Loading the datasets with explicit encoding and handling BOM if present

# Load datasets
datasets = {
    "EmotionalTherapist": pd.read_csv('EmotionalTherapist_Activities.csv', encoding='utf-8-sig'),
    "OccupationalTherapist": pd.read_csv('OccupationalTherapist_Activities.csv', encoding='utf-8-sig'),
    "Physiotherapist": pd.read_csv('Physiotherapist_Activities.csv', encoding='utf-8-sig'),
    "SpeechTherapist": pd.read_csv('SpeechTherapist_Activities.csv', encoding='utf-8-sig')
}








def set_specific_next_intent(context_params, current_intent, next_intent):
    context_params['next_intent'] = next_intent

def get_next_intent(context_params):
    return context_params.get('next_intent')

def set_previous_intent(context_params):
    context_params['previous_intent'] = context_params.get('current_intent')

def set_specific_previous_intent(context_params, intent_name):
    context_params['previous_intent'] = intent_name
    


def clear_context_params(req):
    """Clear context parameters."""
    output_contexts = req.get('queryResult', {}).get('outputContexts', [])
    for context in output_contexts:
            context['parameters'] = {}
    return output_contexts



def clear_specific_context(req, context_name):
    """Clear parameters for a specific context."""
    output_contexts = req.get('queryResult', {}).get('outputContexts', [])
    for context in output_contexts:
        if context.get('name', '').endswith(f'/contexts/{context_name}'):
            context['parameters'] = {}
    return output_contexts



# Helper functions
def get_context_params(req):
    output_contexts = req.get('queryResult', {}).get('outputContexts', [])
    for context in output_contexts:
        if context.get('name', '').endswith('/contexts/activity_selection_context'):
            return context.get('parameters', {})
    return {}

def update_context_params(context_params, new_params):
    context_params.update(new_params)
    return context_params

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    intent_name = req['queryResult']['intent']['displayName']
    dialogflow_session_id = req['session']
    context_params = get_context_params(req)
    logging.debug("webhook context_params: %s", context_params)
    query_text = req['queryResult']["queryText"]


    if query_text == "Show Activities Now":
        set_specific_next_intent(context_params, intent_name, "ShowActivitiesNow")
        set_specific_previous_intent(context_params, intent_name)
    elif query_text == "Show Different Activities":
        set_specific_next_intent(context_params, intent_name, "ShowDifferentGames")
        set_specific_previous_intent(context_params, intent_name)
    elif query_text == "Back to Previous Question":
        return handle_back_to_previous_question(req, dialogflow_session_id)

    if context_params.get('next_intent'):
        logging.debug("Next intent matches current intent. Routing to handle_next_intent.")
        return handle_next_intent(req, dialogflow_session_id, context_params)
    
    return handle_intent(req, dialogflow_session_id)

def handle_intent(req, dialogflow_session_id):
    intent_name = req['queryResult']['intent']['displayName']
    context_params = get_context_params(req)

    if context_params.get('next_intent'):
        logging.debug("Next intent matches current intent. Routing to handle_next_intent.")
        return handle_next_intent(req, dialogflow_session_id, context_params)
    logging.debug("Intent: %s, Dialogflow Session ID: %s", intent_name, dialogflow_session_id)

    if intent_name == "Back to Previous Question":
        return handle_back_to_previous_question(req, dialogflow_session_id)

    elif intent_name == "Default Welcome Intent":
        return handle_welcome_intent(req, dialogflow_session_id)
    elif intent_name == "CaptureTherapistRole":
        return handle_get_therapist_role(req, dialogflow_session_id)
    elif intent_name == "CapturePlayTypeSelection":
        return handle_capture_play_type_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureMotorSkillsSelection":
        return handle_capture_motor_skills_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureLanguageLevelSelection":
        return handle_capture_language_level_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureUnderstandingLevelSelection":
        return handle_capture_understanding_level_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureVocabularySelection":
        return handle_capture_vocabulary_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureADLIndependenceLevelSelection":
        return handle_capture_adl_independence_level_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureGrossMotorSkillsAndOrganizationSelection":
        return handle_capture_gross_motor_skills_and_organization_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureSensoryFocusSelection":
        return handle_capture_sensory_focus_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureExpressesEmotionSelection":
        return handle_capture_expresses_understands_emotion_selection(req, dialogflow_session_id)
    elif intent_name == "CaptureGroupOrIndividualSelection":
        return handle_capture_group_or_individual_selection(req, dialogflow_session_id)
    elif intent_name == "ShowActivitiesNow":
        return handle_show_activities_now(req, dialogflow_session_id)
    elif intent_name == "ShowDifferentGames":
        return handle_show_different_games(req, dialogflow_session_id)
    else:
        return {
        'fulfillmentText': 'Intent handled.'
    }


def handle_next_intent(req, dialogflow_session_id, context_params):
    next_intent = context_params.get('next_intent')
    logging.debug("Next Intent: %s, Dialogflow Session ID: %s", next_intent, dialogflow_session_id)
    logging.debug("Context Params in handle_next_intent: %s", context_params)


    if  next_intent == "Back to Previous Question":
        return handle_back_to_previous_question(req, dialogflow_session_id)
    elif next_intent == "Default Welcome Intent":
        return handle_welcome_intent(req, dialogflow_session_id)
    elif next_intent == "CaptureTherapistRole":
        return handle_get_therapist_role(req, dialogflow_session_id)
    elif next_intent == "CapturePlayTypeSelection":
        return handle_capture_play_type_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureMotorSkillsSelection":
        return handle_capture_motor_skills_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureLanguageLevelSelection":
        return handle_capture_language_level_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureUnderstandingLevelSelection":
        return handle_capture_understanding_level_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureVocabularySelection":
        return handle_capture_vocabulary_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureADLIndependenceLevelSelection":
        return handle_capture_adl_independence_level_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureGrossMotorSkillsAndOrganizationSelection":
        return handle_capture_gross_motor_skills_and_organization_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureSensoryFocusSelection":
        return handle_capture_sensory_focus_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureExpressesEmotionSelection":
        return handle_capture_expresses_understands_emotion_selection(req, dialogflow_session_id)
    elif next_intent == "CaptureGroupOrIndividualSelection":
        return handle_capture_group_or_individual_selection(req, dialogflow_session_id)
    elif next_intent == "ShowActivitiesNow":
        return handle_show_activities_now(req, dialogflow_session_id)
    elif next_intent == "ShowDifferentGames":
        return handle_show_different_games(req, dialogflow_session_id)
    else:
        logging.warning("Next intent not handled: %s", next_intent)
        return jsonify({"fulfillmentText": "Next intent not handled."})
    


def handle_welcome_intent(req, dialogflow_session_id, cleared_contexts=None):
    if cleared_contexts is None:
        cleared_contexts = clear_context_params(req)
    
    logging.debug("Received contexts in handle_welcome_intent: %s", cleared_contexts)
    
    response_text = "Please select your role."
    rich_response = [
        {
            "type": "chips",
            "options": [
                {"text": "EmotionalTherapist"},
                {"text": "OccupationalTherapist"},
                {"text": "Physiotherapist"},
                {"text": "SpeechTherapist"}
            ]
        }
    ]
    
   
    return jsonify({
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": {"richContent": [rich_response]}}
        ],
        "outputContexts": cleared_contexts
    })

def handle_get_therapist_role(req, dialogflow_session_id, preserved_therapist_role=None):
    parameters = req['queryResult']['parameters']
    therapist_role = preserved_therapist_role or parameters.get('therapist_role') or context_params.get('therapist_role', '')
    context_params = {'therapist_role': therapist_role}
    logging.debug("Context Params in handle_get_therapist_role: %s", context_params)
    logging.debug("Therapist Role: %s", therapist_role)

    set_specific_next_intent(context_params, 'CaptureTherapistRole', 'CapturePlayTypeSelection')
    set_previous_intent(context_params)
    response_text = f"Selected {therapist_role}. Now, please choose the play type."
    next_question_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Sensory-Motor"},
                        {"text": "Functional"},
                        {"text": "Imaginative"},
                        {"text": "Socio-Dramatic"}
                    ]
                }
            ]
        ]
    }
  # Create a new activity_selection_context with only the therapist_role
    new_activity_selection_context = {
        "name": f"{dialogflow_session_id}/contexts/activity_selection_context",
        "lifespanCount": 15,
        'parameters': context_params
    }
    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_question_payload}
        ],
        "outputContexts": [new_activity_selection_context]

    })
def handle_capture_play_type_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    play_type = parameters.get('play_type')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'play_type': play_type})
        # Ensure therapist_role is not overwritten
    if 'therapist_role' not in updated_params or not updated_params['therapist_role']:
        updated_params['therapist_role'] = context_params.get('therapist_role_original', '')

    set_specific_next_intent(updated_params, 'CapturePlayTypeSelection', 'CaptureMotorSkillsSelection')
    set_specific_previous_intent(updated_params, 'CaptureTherapistRole')  
    updated_params['current_intent'] = 'CapturePlayTypeSelection'

    logging.debug("Context Params in handle_capture_play_type_selection: %s", context_params)
    logging.debug("Updated context in handle_capture_play_type_selection: %s", updated_params)

    activity_selection_context = {
        "name": f"{dialogflow_session_id}/contexts/activity_selection_context", 
        'lifespanCount': 15,
        'parameters': updated_params
    }

    response_text = f"What is the motor skills level of the child ? "
    motor_skills_context = {
        "name": f"{dialogflow_session_id}/contexts/motor_skills_context", 
        'lifespanCount': 2,
        'parameters': updated_params
    }
    next_question_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Age-appropriate"},
                        {"text": "Below age level"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }
    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_question_payload}
        ],
        "outputContexts": [activity_selection_context,motor_skills_context]
    })
def handle_capture_motor_skills_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    motor_skills = parameters.get('motor_skills')

    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'motor_skills': motor_skills})
    logging.debug("sdmottoe: %s", motor_skills)

    therapist_role = updated_params.get('therapist_role')
    set_specific_previous_intent(updated_params, 'CapturePlayTypeSelection')
    updated_params['current_intent'] = 'CaptureMotorSkillsSelection'
    logging.debug("Context Params in handle_capture_motor_skills_selection: %s", context_params)
    logging.debug("Updated Params in capture motor skills: %s", updated_params)
    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    motor_understanding_level_context = {
        'name': f"{dialogflow_session_id}/contexts/motor_understanding_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    motor_sensory_focus_context = {
        'name': f"{dialogflow_session_id}/contexts/motor_sensory_focus_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    clear_specific_context(req,motor_understanding_level_context)
    clear_specific_context(req,motor_sensory_focus_context)

    if therapist_role in ["EmotionalTherapist", "SpeechTherapist"]:
        response_text = f"What is the sensory you would like the activity to focus on?"
        set_specific_next_intent(updated_params, 'CaptureMotorSkillsSelection', 'CaptureSensoryFocusSelection')


        motor_sensory_focus_context = {
        'name': f"{dialogflow_session_id}/contexts/motor_sensory_focus_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        next_question_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Visual"},
                        {"text": "Proprioceptive"},
                        {"text": "Tactile"},
                        {"text": "Vestibular"},
                        {"text": "Auditory"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }
    elif therapist_role in ["Physiotherapist", "OccupationalTherapist"] :
        response_text = f"What is the Understanding level of the child?"
        set_specific_next_intent(updated_params, 'CaptureMotorSkillsSelection', 'CaptureUnderstandingLevelSelection')


        motor_understanding_level_context = {
        'name': f"{dialogflow_session_id}/contexts/motor_understanding_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        next_question_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Age-appropriate"},
                        {"text": "Below age level"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }
    else:
         
        return jsonify({"ERROR."})

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_question_payload}
        ],
        "outputContexts": [activity_selection_context,motor_sensory_focus_context,  motor_understanding_level_context]
    })

def handle_capture_language_level_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    language_level = parameters.get('language_level')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'language_level': language_level})

    therapist_role = updated_params['therapist_role']
    updated_params['current_intent'] = 'CaptureLanguageLevelSelection'

    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    language_understanding_level_context = {
        'name': f"{dialogflow_session_id}/contexts/language_understanding_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    clear_specific_context(req,'__system_counters__')
    clear_specific_context(req,language_understanding_level_context)

    if therapist_role in ["SpeechTherapist", "EmotionalTherapist"]:

        response_text = f"What is the understanding level of the Child? "
        set_specific_next_intent(updated_params, 'CaptureLanguageLevelSelection', 'CaptureUnderstandingLevelSelection')
        set_specific_previous_intent(updated_params, 'CaptureSensoryFocusSelection')

        language_understanding_level_context = {
        'name': f"{dialogflow_session_id}/contexts/language_understanding_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        next_payload = {
            "richContent": [
                [
                    {
                        "type": "chips",
                        "options": [
                            {"text": "Age-appropriate"},
                            {"text": "Below age level"},
                            {"text": "Show Activities Now"}
                        ]
                    }
                ]
            ]
        }
    else:
        return jsonify({"fulfillmentText": "Therapist role not recognized."})
    logging.debug("updated_paramsParams in handle_capture_language_level_selection: %s", updated_params)  # Log

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}
        ],
        "outputContexts": [
            activity_selection_context,
            language_understanding_level_context
        ]
    })

def handle_capture_understanding_level_selection(req, dialogflow_session_id):

    parameters = req['queryResult']['parameters']
    understanding_level= parameters.get('understanding_level')
    context_params = get_context_params(req)
    logging.debug(f"Extracted understanding_level: {understanding_level}")

    updated_params = update_context_params(context_params, {'understanding_level': understanding_level})
    set_specific_previous_intent(updated_params, 'CaptureLanguageLevelSelection')
    updated_params['current_intent'] = 'CaptureUnderstandingLevelSelection'
    therapist_role = updated_params['therapist_role']
    logging.debug(f"Updated params after understanding level: {updated_params}")


    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    understanding_express_level_context = {
        'name': f"{dialogflow_session_id}/contexts/understanding_express_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    understanding_vocabulary_focus_context = {
        'name': f"{dialogflow_session_id}/contexts/understanding_vocabulary_focus_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    understanding_independence_focus_context = {
        'name': f"{dialogflow_session_id}/contexts/understanding_independence_focus_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    clear_specific_context(req,'__system_counters__')
    clear_specific_context(req,understanding_express_level_context)
    clear_specific_context(req,understanding_vocabulary_focus_context)
    clear_specific_context(req,understanding_independence_focus_context)


    if therapist_role == "SpeechTherapist":
        response_text = f" What is the Child's Vocabulary level?"
        understanding_vocabulary_focus_context = {
        'name': f"{dialogflow_session_id}/contexts/understanding_vocabulary_focus_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        set_specific_next_intent(updated_params, 'CaptureUnderstandingLevelSelection', 'CaptureVocabularySelection')

        next_payload = {
            "richContent": [
                [
                    {
                        "type": "chips",
                        "options": [
                            {"text": "Age-appropriate"},
                            {"text": "Below age level"},
                            {"text": "Show Activities Now"}
                        ]
                    }
                ]
            ]
        }
    elif therapist_role == "EmotionalTherapist":
        response_text = f" Does the child know how to express/understand their emotion?"
        understanding_express_level_context = {
        'name': f"{dialogflow_session_id}/contexts/understanding_express_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        set_specific_next_intent(updated_params, 'CaptureUnderstandingLevelSelection', 'CaptureExpressesEmotionSelection')

        next_payload = {
            "richContent": [
                [
                    {
                        "type": "chips",
                        "options": [
                            {"text": "Yes"},
                            {"text": "No"},
                            {"text": "Show Activities Now"}
                        ]
                    }
                ]
            ]
        }
    elif therapist_role in ["OccupationalTherapist", "Physiotherapist"]:
        response_text = f"What is the ADL(Activities of Daily Living) independence level?"
        understanding_independence_focus_context = {
        'name': f"{dialogflow_session_id}/contexts/understanding_independence_focus_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        set_specific_next_intent(updated_params, 'CaptureUnderstandingLevelSelection', 'CaptureADLIndependenceLevelSelection')

        next_payload = {
            "richContent": [
                [
                    {
                        "type": "chips",
                        "options": [
                            {"text": "Age-appropriate"},
                            {"text": "Below age level"},
                            {"text": "Show Activities Now"}
                        ]
                    }
                ]
            ]
        }
    else:
        return jsonify({"fulfillmentText": "Therapist role not recognized."})
    
    logging.debug("Final updated_params in handle_capture_understanding_level_selection:", updated_params)

 

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}
        ],
        "outputContexts": [
            activity_selection_context,
            understanding_independence_focus_context,
            understanding_express_level_context,
            understanding_vocabulary_focus_context
        ]
    })

def handle_capture_vocabulary_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    vocabulary = parameters.get('vocabulary')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'vocabulary': vocabulary})
    logging.debug("Context Params in handle_capture_vocabulary_selection:", context_params)  # Log

    set_specific_next_intent(updated_params, 'CaptureVocabularySelection', 'CaptureGroupOrIndividualSelection')
    set_specific_previous_intent(updated_params, 'CaptureUnderstandingLevelSelection')
    updated_params['current_intent'] = 'CaptureVocabularySelection'
    response_text = f" Do you prefer group or individual activities?"
 
    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    vocabulary_G_level_context = {
        'name': f"{dialogflow_session_id}/contexts/vocabulary_G_level_context",
        'lifespanCount': 2,
        'parameters': {}
    }
    clear_specific_context(req,'__system_counters__')
    clear_specific_context(req,vocabulary_G_level_context)
    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Individual"},
                        {"text": "Group"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}  ],
        "outputContexts": [
            activity_selection_context,
            vocabulary_G_level_context
        ]
    })

def handle_capture_adl_independence_level_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    adl_independence_level = parameters.get('adl_independence_level')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'adl_independence_level': adl_independence_level})

    set_specific_next_intent(updated_params, 'CaptureADLIndependenceLevelSelection', 'CaptureGrossMotorSkillsAndOrganizationSelection')
    set_specific_previous_intent(updated_params, 'CaptureExpressesEmotionSelection')
    updated_params['current_intent'] = 'CaptureADLIndependenceLevelSelection'
    logging.debug("Context Params in handle_capture_adl_independence_level_selection:", context_params)  # Log

    response_text = f"What is the Gross motor skills level?"

    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    independence_gross_motor_level_context = {
        'name': f"{dialogflow_session_id}/contexts/independence_gross_motor_level_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    clear_specific_context(req,'__system_counters__')
    clear_specific_context(req,independence_gross_motor_level_context)

    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Age-appropriate"},
                        {"text": "Below age level"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}
        ],
        "outputContexts": [
            activity_selection_context,
            independence_gross_motor_level_context
        ]
    })

def handle_capture_gross_motor_skills_and_organization_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    gross_motor_skills_and_organization = parameters.get('gross_motor_skills_and_organization')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'gross_motor_skills_and_organization': gross_motor_skills_and_organization})
    logging.debug("Context Params in handle_capture_gross_motor_skills_and_organization_selection:", context_params)  # Log

    set_specific_previous_intent(updated_params,'CaptureADLIndependenceLevelSelection')

    response_text = f" What is the sensory you would like the activity to focus on?"
    set_specific_next_intent(updated_params, 'CaptureGrossMotorSkillsAndOrganizationSelection', 'CaptureSensoryFocusSelection')

    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    gross_motor_sensory_context = {
        'name': f"{dialogflow_session_id}/contexts/gross_motor_sensory_context",
        'lifespanCount': 2,
        'parameters': {}
    }
    clear_specific_context(req,'__system_counters__')
    clear_specific_context(req,gross_motor_sensory_context)
    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Visual"},
                        {"text": "Proprioceptive"},
                        {"text": "Tactile"},
                        {"text": "Vestibular"},
                        {"text": "Auditory"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}
        ],
        "outputContexts": [
            activity_selection_context,
            gross_motor_sensory_context
        ]
    })

def handle_capture_sensory_focus_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    sensory_focus = parameters.get('sensory_focus')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'sensory_focus': sensory_focus})
    updated_params['current_intent'] = 'CaptureSensoryFocusSelection'
    
    therapist_role = updated_params['therapist_role']

    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    sensory_language_context = {
        'name': f"{dialogflow_session_id}/contexts/sensory_language_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
    sensory_I_context = {
        'name': f"{dialogflow_session_id}/contexts/sensory_I_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }

    if therapist_role in ["EmotionalTherapist", "SpeechTherapist"]:
        response_text = f"Whais the Child's language level?"
      

        sensory_language_context = {
        'name': f"{dialogflow_session_id}/contexts/sensory_language_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        set_specific_next_intent(updated_params, 'CaptureSensoryFocusSelection', 'CaptureLanguageLevelSelection')
        set_specific_previous_intent(updated_params, 'CaptureMotorSkillsSelection')

        next_payload = {
            "richContent": [
                [
                    {
                        "type": "chips",
                        "options": [
                            {"text": "Age-appropriate"},
                            {"text": "Below age level"},
                            {"text": "Show Activities Now"}
                        ]
                    }
                ]
            ]
        }
    elif therapist_role in ["OccupationalTherapist", "Physiotherapist"]:
        response_text = f"Do you prefer group or individual activities?"
        sensory_I_context = {
        'name': f"{dialogflow_session_id}/contexts/sensory_I_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }
        set_specific_next_intent(updated_params, 'CaptureSensoryFocusSelection', 'CaptureGroupOrIndividualSelection')
        set_specific_previous_intent(updated_params, 'CaptureGrossMotorSkillsAndOrganizationSelection')

        next_payload = {
            "richContent": [
                [
                    {
                        "type": "chips",
                        "options": [
                            {"text": "Individual"},
                            {"text": "Group"},
                            {"text": "Show Activities Now"}
                        ]
                    }
                ]
            ]
        }
    else:
        return jsonify({"fulfillmentText": "Therapist role not recognized."})
    logging.debug("Contsdfsfsfsfsmotor_skills_selection: %s", context_params)

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}
        ],
        "outputContexts": [activity_selection_context,sensory_language_context,sensory_I_context]
    })

def handle_capture_expresses_understands_emotion_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    expresses_understands_emotion = parameters.get('expresses_understands_emotion')
    context_params = get_context_params(req)
    updated_params = update_context_params(context_params, {'expresses_understands_emotion': expresses_understands_emotion})
    set_specific_next_intent(updated_params, 'CaptureExpressesEmotionSelection', 'CaptureGroupOrIndividualSelection')
    set_specific_previous_intent(updated_params, 'CaptureUnderstandingLevelSelection')
    updated_params['current_intent'] = 'CaptureExpressesEmotionSelection'

    response_text = f"Do you prefer group or individual activities?"
    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }
    expresses_a_context = {
        'name': f"{dialogflow_session_id}/contexts/expresses_a_context",
        'lifespanCount': 2,
        'parameters': updated_params
    }

    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Individual"},
                        {"text": "Group"},
                        {"text": "Show Activities Now"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": response_text,
        "fulfillmentMessages": [
            {"text": {"text": [response_text]}},
            {"payload": next_payload}
        ],
        "outputContexts": [activity_selection_context,expresses_a_context]
    })

def handle_capture_group_or_individual_selection(req, dialogflow_session_id):
    parameters = req['queryResult']['parameters']
    group_or_individual = parameters.get('group_or_individual')
    context_params = get_context_params(req)

    updated_params = update_context_params(context_params, {'group_or_individual': group_or_individual})
    therapist_role = updated_params.get('therapist_role')
    updated_params['current_intent'] = 'CaptureGroupOrIndividualSelection'
    if therapist_role == "EmotionalTherapist":
        set_specific_previous_intent(updated_params, 'CaptureExpressesEmotionSelection')
    elif therapist_role == "SpeechTherapist":
        set_specific_previous_intent(updated_params, 'CaptureVocabularySelection')
    else:  # OccupationalTherapist or Physiotherapist
        set_specific_previous_intent(updated_params, 'CaptureSensoryFocusSelection')

    set_specific_next_intent(updated_params, 'CaptureGroupOrIndividualSelection', 'ShowActivitiesNow')
    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': updated_params
    }

    params_list = ", ".join([f"{key}: {value}" for key, value in updated_params.items()])
    logging.debug("params_list in handle_capture_group_or_individual_selection : %s", params_list)

    response_text = f"Here are your selections:"

    activities_response = show_activities(updated_params)

    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Show Different Activities"},
                        {"text": "Back to Previous Question"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": response_text + "\n\n" + activities_response,
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [response_text + "\n\n" + activities_response]
                }
            },
            {
                "payload": next_payload
            }
        ],
        "outputContexts": [activity_selection_context]
    })
def filter_emotional_activities(dataset, **filters):
    filtered_df = dataset.copy()

    if 'Play Type' in filters and filters['Play Type']:
        filtered_df = filtered_df[filtered_df['Play Type'].str.contains(filters['Play Type'], case=False, na=False)]

    if 'Motor Skills Level' in filters and filters['Motor Skills Level']:
        filtered_df = filtered_df[filtered_df['Motor Skills Level'].str.contains(filters['Motor Skills Level'], case=False, na=False)]

    if 'Understanding Level' in filters and filters['Understanding Level']:
        filtered_df = filtered_df[filtered_df['Understanding Level'].str.contains(filters['Understanding Level'], case=False, na=False)]

    if 'Sensory Focus' in filters and filters['Sensory Focus']:
        filtered_df = filtered_df[filtered_df['Sensory Focus'].str.contains(filters['Sensory Focus'], case=False, na=False)]

    if 'Language Level' in filters and filters['Language Level']:
        filtered_df = filtered_df[filtered_df['Language Level'].str.contains(filters['Language Level'], case=False, na=False)]

    if 'Expresses/Understands Emotion' in filters and filters['Expresses/Understands Emotion']:
        filtered_df = filtered_df[filtered_df['Expresses/Understands Emotion'].str.contains(filters['Expresses/Understands Emotion'], case=False, na=False)]

    if 'Group or Individual' in filters and filters['Group or Individual']:
        filtered_df = filtered_df[filtered_df['Group or Individual'].str.contains(filters['Group or Individual'], case=False, na=False)]

    if 'previously_shown_ids' in filters and filters['previously_shown_ids']:
        filtered_df = filtered_df[~filtered_df.index.isin(filters['previously_shown_ids'])]

    return filtered_df


def filter_speech_activities(dataset, **filters):
    filtered_df = dataset.copy()
    
    if 'Play Type' in filters and filters['Play Type']:
        filtered_df = filtered_df[filtered_df['Play Type'].str.contains(filters['Play Type'], case=False, na=False)]
    if 'Motor Skills Level' in filters and filters['Motor Skills Level']:
        filtered_df = filtered_df[filtered_df['Motor Skills Level'].str.contains(filters['Motor Skills Level'], case=False, na=False)]
    if 'Sensory Focus' in filters and filters['Sensory Focus']:
        filtered_df = filtered_df[filtered_df['Sensory Focus'].str.contains(filters['Sensory Focus'], case=False, na=False)]
    if 'Understanding Level' in filters and filters['Understanding Level']:
        filtered_df = filtered_df[filtered_df['Understanding Level'].str.contains(filters['Understanding Level'], case=False, na=False)]
    if 'Language Level' in filters and filters['Language Level']:
        filtered_df = filtered_df[filtered_df['Language Level'].str.contains(filters['Language Level'], case=False, na=False)]
    if 'Vocabulary' in filters and filters['Vocabulary']:
        filtered_df = filtered_df[filtered_df['Vocabulary'].str.contains(filters['Vocabulary'], case=False, na=False)]
    if 'Group or Individual' in filters and filters['Group or Individual']:
        filtered_df = filtered_df[filtered_df['Group or Individual'].str.contains(filters['Group or Individual'], case=False, na=False)]
    if 'previous_ids' in filters:
        filtered_df = filtered_df[~filtered_df.index.isin(filters['previous_ids'])]

    return filtered_df


def filter_occupational_physio_activities(dataset, **filters):
    filtered_df = dataset.copy()
    
    if 'Play Type' in filters and filters['Play Type']:
        filtered_df = filtered_df[filtered_df['Play Type'].str.contains(filters['Play Type'], case=False, na=False)]
    if 'Sensory Focus' in filters and filters['Sensory Focus']:
        filtered_df = filtered_df[filtered_df['Sensory Focus'].str.contains(filters['Sensory Focus'], case=False, na=False)]
    if 'Motor Skills Level' in filters and filters['Motor Skills Level']:
        filtered_df = filtered_df[filtered_df['Motor Skills Level'].str.contains(filters['Motor Skills Level'], case=False, na=False)]
    if 'ADL Independence Level' in filters and filters['ADL Independence Level']:
        filtered_df = filtered_df[filtered_df['ADL Independence Level'].str.contains(filters['ADL Independence Level'], case=False, na=False)]
    if 'Understanding Level' in filters and filters['Understanding Level']:
        filtered_df = filtered_df[filtered_df['Understanding Level'].str.contains(filters['Understanding Level'], case=False, na=False)]
    if 'Gross Motor Skills and Organization' in filters and filters['Gross Motor Skills and Organization']:
        filtered_df = filtered_df[filtered_df['Gross Motor Skills and Organization'].str.contains(filters['Gross Motor Skills and Organization'], case=False, na=False)]
    if 'Group or Individual' in filters and filters['Group or Individual']:
        filtered_df = filtered_df[filtered_df['Group or Individual'].str.contains(filters['Group or Individual'], case=False, na=False)]
    if 'previous_ids' in filters:
        filtered_df = filtered_df[~filtered_df.index.isin(filters['previous_ids'])]

    return filtered_df


def handle_show_activities_now(req, dialogflow_session_id):
    context_params = get_context_params(req)
    context_params['current_intent'] = "ShowActivitiesNow"
     # Define the order of questions
    question_order = [
        'therapist_role', 
        'play_type', 
        'motor_skills', 
        'sensory_focus',
        'language_level', 
        'understanding_level',
        'vocabulary',
        'expresses_understands_emotion', 
        'adl_independence_level',
        'gross_motor_skills_and_organization',
        'group_or_individual'
    ]
    filtered_params = {}
    for param in question_order:
        if param in context_params and context_params[param]:
            filtered_params[param] = context_params[param]
        else:
            # Stop when we reach a parameter that hasn't been answered
            break
    logging.debug(f"Filtered params for show_activities: {filtered_params}")

    activities_response = show_activities(context_params)
    
    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Show Different Activities"},
                        {"text": "Back to Previous Question"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": activities_response,
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [activities_response]
                }
            },
            {
                "payload": next_payload
            }
        ],
        "outputContexts": [
            {
                'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
                'lifespanCount': 15,
                'parameters': context_params
            }
        ]
    })

def show_activities(context_params):
    print("Context Params in show_activities:", context_params)  # Log

    therapist_role = context_params.get('therapist_role')
    if therapist_role not in datasets:
        return "Therapist role not recognized."
    
    dataset = datasets[therapist_role]

    filters = {
        'Play Type': context_params.get('play_type'),
        'Motor Skills Level': context_params.get('motor_skills'),
        'Sensory Focus': context_params.get('sensory_focus'),
        'Language Level': context_params.get('language_level'),
        'Expresses/Understands Emotion': context_params.get('expresses_understands_emotion'),
        'Group or Individual': context_params.get('group_or_individual'),
        'ADL Independence Level': context_params.get('adl_independence_level'),
        'Understanding Level': context_params.get('understanding_level'),
        'Gross Motor Skills and Organization': context_params.get('gross_motor_skills_and_organization'),
        'Vocabulary': context_params.get('vocabulary'),
        'previously_shown_ids': context_params.get('previously_shown_ids', [])
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    logging.debug(f"Filters: {filters}")

    if therapist_role == "EmotionalTherapist":
        filtered_df = filter_emotional_activities(dataset, **filters)
    elif therapist_role == "SpeechTherapist":
        filtered_df = filter_speech_activities(dataset, **filters)
    elif therapist_role in ["OccupationalTherapist", "Physiotherapist"]:
        filtered_df = filter_occupational_physio_activities(dataset, **filters)
    else:
        return "Therapist role not recognized."

    #logging.debug(f"Filtered dataframe before applying previous_ids exclusion: {filtered_df}")

    # Check if filtered dataframe is empty
    if filtered_df.empty:
        return "No activities found based on the current selections."

    # Exclude previously shown activities
    filtered_df = filtered_df[~filtered_df.index.isin(filters['previously_shown_ids'])]

    #logging.debug(f"Filtered dataframe after applying previous_ids exclusion: {filtered_df}")

    # Check if filtered dataframe is empty after excluding previously shown activities
    if filtered_df.empty:
        return "No new activities found based on the current selections."

    # Select two activities to display
    selected_activities = filtered_df.sample(n=min(2, len(filtered_df)))

    # Update previously shown IDs
    new_shown_ids = selected_activities.index.tolist()
    previous_ids = filters['previously_shown_ids']
    previous_ids.extend(new_shown_ids)
    updated_params = update_context_params(context_params, {'previously_shown_ids': previous_ids})
    logging.debug("updated_params show activity function: %s", updated_params)

    # Convert activities to a list of dictionaries
    activities_list = selected_activities[['Activity Name', 'Description', 'Materials Needed', 'Environmental Adaptation']].to_dict(orient='records')

    response_text = "Here are the activities based on your current selections:\n\n"
    for activity in activities_list:
        response_text += f"+{'-'*25}+\n"
        response_text += f"| Activity Name           : {activity['Activity Name']}\n"
        response_text += f"+{'-'*25}+\n"
        response_text += f"| Description             : {activity['Description']}\n"
        response_text += f"+{'-'*25}+\n"
        response_text += f"| Materials Needed        : {activity['Materials Needed']}\n"
        response_text += f"+{'-'*25}+\n"
        response_text += f"| Environmental Adaptation: {activity['Environmental Adaptation']}\n"
        response_text += f"+{'-'*25}+\n\n"

    return response_text

def handle_show_different_games(req, dialogflow_session_id):
    context_params = get_context_params(req)
    context_params['current_intent'] = "ShowDifferentGames"

    activities_response = show_activities(context_params)
    
    next_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Show Different Activities"},
                        {"text": "Back to Previous Question"}
                    ]
                }
            ]
        ]
    }

    return jsonify({
        "fulfillmentText": activities_response,
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [activities_response]
                }
            },
            {
                "payload": next_payload
            }
        ],
        "outputContexts": [
            {
                'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
                'lifespanCount': 15,
                'parameters': context_params
            }
        ]
    })

def handle_back_to_previous_question(req, dialogflow_session_id):
    context_params = get_context_params(req)
    current_intent = context_params.get('current_intent', '')
    therapist_role = context_params.get('therapist_role', context_params.get('therapist_role_original', ''))

    logging.debug(f"handle_back_to_previous_question therapist_role: {therapist_role}")

    logging.debug(f"handle_back_to_previous_question Current intent: {current_intent}")
    logging.debug(f"handle_back_to_previous_question Context params: {context_params}")

 # Define the order of intents for each therapist role
    intent_order = {
        "EmotionalTherapist": [
            "CaptureTherapistRole",
            "CapturePlayTypeSelection",
            "CaptureMotorSkillsSelection",
            "CaptureSensoryFocusSelection",
            "CaptureLanguageLevelSelection",
            "CaptureUnderstandingLevelSelection",
            "CaptureExpressesEmotionSelection",
            "CaptureGroupOrIndividualSelection"
        ],
        "SpeechTherapist": [
            "CaptureTherapistRole",
            "CapturePlayTypeSelection",
            "CaptureMotorSkillsSelection",
            "CaptureSensoryFocusSelection",
            "CaptureLanguageLevelSelection",
            "CaptureUnderstandingLevelSelection",
            "CaptureVocabularySelection",
            "CaptureGroupOrIndividualSelection"
        ],
        "OccupationalTherapist": [
            "CaptureTherapistRole",
            "CapturePlayTypeSelection",
            "CaptureMotorSkillsSelection",
            "CaptureUnderstandingLevelSelection",
            "CaptureADLIndependenceLevelSelection",
            "CaptureGrossMotorSkillsAndOrganizationSelection",
            "CaptureSensoryFocusSelection",
            "CaptureGroupOrIndividualSelection"
        ],
        "Physiotherapist": [
            "CaptureTherapistRole",
            "CapturePlayTypeSelection",
            "CaptureMotorSkillsSelection",
            "CaptureUnderstandingLevelSelection",
            "CaptureADLIndependenceLevelSelection",
            "CaptureGrossMotorSkillsAndOrganizationSelection",
            "CaptureSensoryFocusSelection",
            "CaptureGroupOrIndividualSelection"
        ]
    }

    current_intent_order = intent_order.get(therapist_role, [])

    # Find all answered questions
    answered_questions = []
    for intent in current_intent_order:
        logging.debug(f"intent in handle back for loop : {intent}")
        if intent == "CaptureTherapistRole" and context_params.get('therapist_role'):
            answered_questions.append(intent)
        elif intent == "CapturePlayTypeSelection" and context_params.get('play_type'):
            answered_questions.append(intent)
        elif intent == "CaptureMotorSkillsSelection" and context_params.get('motor_skills'):
            answered_questions.append(intent)
        elif intent == "CaptureSensoryFocusSelection" and context_params.get('sensory_focus'):
            answered_questions.append(intent)
        elif intent == "CaptureLanguageLevelSelection" and context_params.get('language_level'):
            answered_questions.append(intent)
        elif intent == "CaptureUnderstandingLevelSelection" and context_params.get('understanding_level'):
            answered_questions.append(intent)
        elif intent == "CaptureExpressesEmotionSelection" and context_params.get('expresses_understands_emotion'):
            answered_questions.append(intent)
        elif intent == "CaptureGroupOrIndividualSelection" and context_params.get('group_or_individual'):
            answered_questions.append(intent)
        logging.debug(f"intent: {intent}, value: {context_params.get(intent.lower().replace('capture', '').replace('selection', ''))}")

    logging.debug(f"Answered questions: {answered_questions}")

    if not answered_questions:
        previous_intent = "CaptureTherapistRole"
    elif current_intent == "ShowActivitiesNow":
        previous_intent = answered_questions[-1]
    else:
        try:
            current_index = answered_questions.index(current_intent)
            previous_intent = answered_questions[current_index - 1] if current_index > 0 else "CaptureTherapistRole"
        except ValueError:
            previous_intent = answered_questions[-1] if answered_questions else "CaptureTherapistRole"

    logging.debug(f"Going back to: {previous_intent}")

    # Set the next intent to be the previous intent
    set_specific_next_intent(context_params, current_intent, previous_intent)

    # Update the previous intent
    if previous_intent != "CaptureTherapistRole":
        new_previous_index = answered_questions.index(previous_intent) - 1
        new_previous = answered_questions[new_previous_index] if new_previous_index >= 0 else "CaptureTherapistRole"
        set_specific_previous_intent(context_params, new_previous)

    # Clear any context specific to the current question
    output_contexts = req.get('queryResult', {}).get('outputContexts', [])
    for context in output_contexts:
        if context.get('name', '').endswith(f'/contexts/{current_intent.lower()}_context'):
            context['parameters'] = {}

    # Update the activity_selection_context
    context_params['current_intent'] = previous_intent
    activity_selection_context = {
        'name': f"{dialogflow_session_id}/contexts/activity_selection_context",
        'lifespanCount': 15,
        'parameters': context_params
    }

    logging.debug(f"Updated context_params in handle_back_to_previous_question: {context_params}")


    # Directly call the handler for the previous intent
    if previous_intent == "CaptureTherapistRole":
        return handle_get_therapist_role(req, dialogflow_session_id, therapist_role)
    elif previous_intent == "CapturePlayTypeSelection":
        return handle_capture_play_type_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureMotorSkillsSelection":
        return handle_capture_motor_skills_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureSensoryFocusSelection":
        return handle_capture_sensory_focus_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureLanguageLevelSelection":
        return handle_capture_language_level_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureUnderstandingLevelSelection":
        return handle_capture_understanding_level_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureVocabularySelection":
        return handle_capture_vocabulary_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureExpressesEmotionSelection":
        return handle_capture_expresses_understands_emotion_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureADLIndependenceLevelSelection":
        return handle_capture_adl_independence_level_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureGrossMotorSkillsAndOrganizationSelection":
        return handle_capture_gross_motor_skills_and_organization_selection(req, dialogflow_session_id)
    elif previous_intent == "CaptureGroupOrIndividualSelection":
        return handle_capture_group_or_individual_selection(req, dialogflow_session_id)
    else:
        response_text = f"Let's go back to the previous question about {previous_intent.replace('Capture', '').replace('Selection', '')}."
        return jsonify({
            "fulfillmentText": response_text,
            "outputContexts": [activity_selection_context]
        })


# Main entry point
if __name__ == '__main__':
    app.run(debug=True)
