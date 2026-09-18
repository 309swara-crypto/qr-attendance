from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn, True
    else:
        import sqlite3
        conn = sqlite3.connect('attendance.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn, False

def init_db():
    conn, is_pg = get_db()
    cur = conn.cursor()
    if is_pg:
        cur.execute("CREATE TABLE IF NOT EXISTS students (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, roll_no TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS teachers (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS attendance (id SERIAL PRIMARY KEY, name TEXT, roll_no TEXT, email TEXT, timestamp TEXT, date TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, roll_no TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, roll_no TEXT, email TEXT, timestamp TEXT, date TEXT)")
    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "attendance_secret_123")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

oauth = OAuth(app)
google = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(name='google', client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET, server_metadata_url='https://accounts.google.com/.well-known/openid-configuration', client_kwargs={'scope': 'openid email profile'})

init_db()

def query_db(query, args=(), one=False, commit=False):
    conn, is_pg = get_db()
    cur = conn.cursor()
    q = query.replace('?', '%s') if is_pg else query
    cur.execute(q, args)
    if commit:
        conn.commit()
        conn.close()
        return None
    result = cur.fetchone() if one else cur.fetchall()
    conn.close()
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password'); role = request.form.get('role')
        if not role:
            flash("Select role"); return render_template('login.html')
        table = 'teachers' if role == 'teacher' else 'students'
        user = query_db(f"SELECT * FROM {table} WHERE username =?", (username,), one=True)
        if user and check_password_hash(user[2], password):
            session['user']=user[1]; session['name']=user[3]; session['role']=role
            if role=='student': session['roll_no']=user[4] if len(user)>4 else ''
            return redirect(url_for('teacher_dashboard' if role=='teacher' else 'student_dashboard'))
        flash("Invalid username or password")
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username=request.form.get('username'); password=request.form.get('password'); name=request.form.get('name'); roll_no=request.form.get('roll_no'); role=request.form.get('role')
        hashed=generate_password_hash(password)
        try:
            if role=='teacher':
                query_db("INSERT INTO teachers (username,password,name) VALUES (?,?,?)",(username,hashed,name),commit=True)
            else:
                query_db("INSERT INTO students (username,password,name,roll_no) VALUES (?,?,?,?)",(username,hashed,name,roll_no),commit=True)
            flash("Registered! Login now"); return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {e}")
    return render_template('register.html')

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if session.get('role')!='teacher': return redirect(url_for('login'))
    records=query_db("SELECT * FROM attendance ORDER BY id DESC")
    return render_template('teacher_dashboard.html', records=records, name=session.get('name'))

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role')!='student': return redirect(url_for('login'))
    return render_template('student_dashboard.html', name=session.get('name'), roll_no=session.get('roll_no'))

@app.route('/login/google')
def google_login():
    if not google: flash("Google not configured"); return redirect(url_for('login'))
    return google.authorize_redirect(url_for('google_callback', _external=True))

@app.route('/callback/google')
def google_callback():
    try:
        token=google.authorize_access_token()
        info=token.get('userinfo') or google.get('https://openidconnect.googleapis.com/v1/userinfo').json()
        session['email']=info.get('email'); session['name']=info.get('name'); session['user']=info.get('email'); session['role']='student'
        return redirect(url_for('student_dashboard'))
    except Exception as e:
        flash(f"Google failed {e}"); return redirect(url_for('login'))

@app.route('/scan')
def scan_qr():
    return render_template('scan_qr.html')

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data=request.get_json() if request.is_json else request.form
    name=data.get('name') or session.get('name') or 'Unknown'
    roll_no=data.get('roll_no') or session.get('roll_no') or ''
    email=session.get('email') or data.get('email') or session.get('user') or ''
    now=datetime.now()
    timestamp=now.strftime("%Y-%m-%d %H:%M:%S"); date_str=now.strftime("%Y-%m-%d")
    try:
        query_db("INSERT INTO attendance (name,roll_no,email,timestamp,date) VALUES (?,?,?,?,?)",(name,roll_no,email,timestamp,date_str),commit=True)
        return jsonify({"success":True,"message":f"Marked {name} at {timestamp}"})
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}),500

@app.route('/report')
@app.route('/attendance_report')
def report():
    records=query_db("SELECT * FROM attendance ORDER BY id DESC")
    return render_template('report.html', records=records)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
