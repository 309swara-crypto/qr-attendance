from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from authlib.integrations.flask_client import OAuth
import os
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
try:
    import segno
except:
    segno = None
import sqlite3

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
DATABASE_URL = os.environ.get("DATABASE_URL")

# ---------------- DB HELPER - FIXES DATA DELETION ----------------
def get_db():
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn, True
    else:
        conn = sqlite3.connect('attendance.db', check_same_thread=False)
        return conn, False

def init_db():
    conn, is_pg = get_db()
    cur = conn.cursor()
    if is_pg:
        cur.execute("""CREATE TABLE IF NOT EXISTS students (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, roll_no TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS teachers (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS attendance (id SERIAL PRIMARY KEY, name TEXT, roll_no TEXT, email TEXT, timestamp TIMESTAMP, date TEXT, student_id TEXT)""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, roll_no TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, roll_no TEXT, email TEXT, timestamp TEXT, date TEXT, student_id TEXT)""")
    conn.commit()
    conn.close()

# ---------------- FLASK APP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "attendance123")
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

init_db()

# ... KEEP ALL YOUR EXISTING ROUTES BELOW THIS ...
# IMPORTANT: For attendance marking, use this logic (NO duplicate block):

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json() or request.form
    name = data.get('name') or session.get('name') or 'Student'
    roll_no = data.get('roll_no') or session.get('roll_no') or ''
    email = session.get('email') or data.get('email') or ''
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    
    # FIXED: No check for existing attendance - allows multiple per day
    conn, is_pg = get_db()
    cur = conn.cursor()
    if is_pg:
        cur.execute("INSERT INTO attendance (name, roll_no, email, timestamp, date) VALUES (%s,%s,%s,%s,%s)", (name, roll_no, email, timestamp, date_str))
    else:
        cur.execute("INSERT INTO attendance (name, roll_no, email, timestamp, date) VALUES (?,?,?,?,?)", (name, roll_no, email, timestamp, date_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Attendance marked at {timestamp}"})
