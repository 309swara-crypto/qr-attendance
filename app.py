from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "qr_attendance_secret_123"
DB = "database.db"

def init_db():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, class TEXT, email TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, roll TEXT, name TEXT, class TEXT, date TEXT, time TEXT, subject TEXT, lat REAL, lon REAL)")
    con.commit()
    con.close()

init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['POST'])
def login():
    role = request.form.get('role')
    id_val = request.form.get('id', '').strip()
    pwd = request.form.get('password', '').strip()

    if role == 'teacher':
        if id_val.lower() == 'maths' and pwd == '1234':
            session['teacher'] = True
            return redirect('/teacher_dashboard')
        return "Invalid Teacher ID/Pass! Use maths / 1234 <a href='/'>Back</a>"
    else:
        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("SELECT roll,name,class FROM students WHERE roll=? AND LOWER(name)=LOWER(?)", (id_val, pwd))
        row = c.fetchone()
        con.close()
        if row:
            session['student_roll'] = row[0]
            session['student_name'] = row[1]
            session['student_class'] = row[2]
            return redirect('/student_dashboard')
        return f"Student not found! Roll:{id_val} Name:{pwd} not matched. Ask teacher to add. <a href='/'>Back</a>"

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if not session.get('teacher'):
        return redirect('/')
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("SELECT * FROM students ORDER BY roll")
    students = c.fetchall()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT roll,name,class,date,time,subject FROM attendance WHERE date=? ORDER BY id DESC", (today,))
    attendance = c.fetchall()
    con.close()
    return render_template('teacher_dashboard.html', students=students, attendance=attendance)

@app.route('/student_dashboard')
def student_dashboard():
    if not session.get('student_roll'):
        return redirect('/')
    roll = session.get('student_roll')
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("SELECT date,time,subject FROM attendance WHERE roll=? ORDER BY id DESC", (roll,))
    my_att = c.fetchall()
    con.close()
    return render_template('student_dashboard.html', roll=roll, name=session.get('student_name'), sclass=session.get('student_class'), attendance=my_att)

@app.route('/add_student', methods=['POST'])
def add_student():
    if not session.get('teacher'):
        return redirect('/')
    name = request.form.get('name', '').strip()
    roll = request.form.get('roll', '').strip()
    sclass = request.form.get('class', '').strip()
    email = request.form.get('email', '').strip()
    if not roll or not name:
        return "Roll and Name required <a href='/teacher_dashboard'>Back</a>"
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("INSERT OR REPLACE INTO students VALUES (?,?,?,?)", (roll, name, sclass, email))
    con.commit()
    con.close()
    return redirect('/teacher_dashboard')

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if not session.get('student_roll'):
        return jsonify({"ok": False})
    data = request.get_json()
    roll = session.get('student_roll')
    name = session.get('student_name')
    sclass = session.get('student_class')
    sub = data.get('sub', 'maths')
    lat = data.get('lat', 0)
    lon = data.get('lon', 0)
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("SELECT id FROM attendance WHERE roll=? AND date=? AND subject=?", (roll, today, sub))
    if c.fetchone():
        con.close()
        return jsonify({"ok": False, "msg": "Already marked"})
    c.execute("INSERT INTO attendance (roll,name,class,date,time,subject,lat,lon) VALUES (?,?,?,?,?,?,?,?)", (roll, name, sclass, today, now_time, sub, lat, lon))
    con.commit()
    con.close()
    return jsonify({"ok": True})

@app.route('/google_login', methods=['POST'])
def google_login():
    data = request.get_json()
    role = data.get('role')
    email = data.get('email')
    name = data.get('name')
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("SELECT roll,name,class FROM students WHERE email=?", (email,))
    row = c.fetchone()
    con.close()
    if row:
        if role == 'student':
            session['student_roll'] = row[0]
            session['student_name'] = row[1]
            session['student_class'] = row[2]
            return jsonify({"redirect": "/student_dashboard"})
        else:
            session['teacher'] = True
            return jsonify({"redirect": "/teacher_dashboard"})
    else:
        return jsonify({"need_details": True, "email": email, "name": name})

@app.route('/google_form')
def google_form():
    email = request.args.get('email', '')
    name = request.args.get('name', '')
    return render_template('google_form.html', email=email, name=name)

@app.route('/google_complete_register', methods=['POST'])
def google_complete_register():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    roll = data.get('roll')
    sclass = data.get('class')
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("INSERT OR REPLACE INTO students VALUES (?,?,?,?)", (roll, name, sclass, email))
    con.commit()
    con.close()
    session['student_roll'] = roll
    session['student_name'] = name
    session['student_class'] = sclass
    return jsonify({"redirect": "/student_dashboard"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
