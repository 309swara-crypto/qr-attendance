import os
import psycopg2
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "qr_attendance_secret_123"

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    else:
        conn = sqlite3.connect('attendance.db')
        return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                roll_no TEXT,
                name TEXT,
                class_name TEXT,
                date TEXT,
                time TEXT,
                email TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                roll_no TEXT UNIQUE,
                name TEXT,
                class_name TEXT,
                email TEXT
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT,
                name TEXT,
                class_name TEXT,
                date TEXT,
                time TEXT,
                email TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT UNIQUE,
                name TEXT,
                class_name TEXT,
                email TEXT
            )
        """)
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    if 'email' not in session:
        return render_template('login.html')
    return render_template('home.html',
        name=session.get('name'),
        roll=session.get('roll'),
        class_name=session.get('class_name'),
        email=session.get('email'))

@app.route('/google_form')
def google_form():
    try:
        email = request.args.get('email')
        name = request.args.get('name')
        if not email:
            return "Email missing from Google", 400
        session['email'] = email
        session['name'] = name
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("SELECT roll_no, class_name FROM students WHERE email=%s", (email,))
        else:
            cur.execute("SELECT roll_no, class_name FROM students WHERE email=?", (email,))
        row = cur.fetchone()
        if row:
            session['roll'] = row[0]
            session['class_name'] = row[1]
            conn.close()
            return redirect('/')
        else:
            conn.close()
            return render_template('google_register.html', email=email, name=name)
    except Exception as e:
        print("ERROR in google_form:", e)
        return f"Internal Error: {e}", 500

@app.route('/register_student', methods=['POST'])
def register_student():
    roll = request.form['roll']
    class_name = request.form['class_name']
    email = session.get('email')
    name = session.get('name')
    conn = get_db()
    cur = conn.cursor()
    try:
        if DATABASE_URL:
            cur.execute("INSERT INTO students (roll_no, name, class_name, email) VALUES (%s,%s,%s,%s)",
                        (roll, name, class_name, email))
        else:
            cur.execute("INSERT INTO students (roll_no, name, class_name, email) VALUES (?,?,?,?)",
                        (roll, name, class_name, email))
        conn.commit()
    except Exception as e:
        print(e)
    conn.close()
    session['roll'] = roll
    session['class_name'] = class_name
    return redirect('/')

@app.route('/mark_attendance')
def mark_attendance():
    if 'email' not in session:
        return redirect('/')
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("SELECT * FROM attendance WHERE email=%s AND date=%s", (session['email'], date))
    else:
        cur.execute("SELECT * FROM attendance WHERE email=? AND date=?", (session['email'], date))
    if cur.fetchone():
        conn.close()
        return "<h3>Already marked today!</h3><a href='/'>Back</a>"
    if DATABASE_URL:
        cur.execute("INSERT INTO attendance (roll_no, name, class_name, date, time, email) VALUES (%s,%s,%s,%s,%s,%s)",
                    (session['roll'], session['name'], session['class_name'], date, time, session['email']))
    else:
        cur.execute("INSERT INTO attendance (roll_no, name, class_name, date, time, email) VALUES (?,?,?,?,?,?)",
                    (session['roll'], session['name'], session['class_name'], date, time, session['email']))
    conn.commit()
    conn.close()
    return "<h3>Attendance Marked Successfully!</h3><a href='/'>Back to Home</a>"

@app.route('/my_attendance')
def my_attendance():
    if 'email' not in session:
        return redirect('/')
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("SELECT date, time FROM attendance WHERE email=%s ORDER BY date DESC", (session['email'],))
    else:
        cur.execute("SELECT date, time FROM attendance WHERE email=? ORDER BY date DESC", (session['email'],))
    records = cur.fetchall()
    conn.close()
    return render_template('my_attendance.html', records=records, name=session.get('name'), roll=session.get('roll'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
