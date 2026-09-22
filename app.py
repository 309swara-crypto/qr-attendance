from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "qr-attendance-final-2024"

DB="/tmp/attendance.db"

def init_db():
    con=sqlite3.connect(DB)
    c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, class TEXT, email TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, roll TEXT, name TEXT, class TEXT, date TEXT, time TEXT, lat REAL, lon REAL, subject TEXT)")
    con.commit()
    con.close()

init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/google_form')
def google_form():
    try:
        email=request.args.get('email','')
        name=request.args.get('name','')
        return render_template('google_form.html', email=email, name=name)
    except Exception as e:
        # If template missing, no 500 error - inline page
        email=request.args.get('email','')
        name=request.args.get('name','')
        return f"""
        <html><body style="font-family:Arial;text-align:center;padding:30px">
        <h3>Complete Registration</h3>
        <p>{email}<br>{name}</p>
        <input id='roll' placeholder='Roll No e.g. 71'><br><br>
        <select id='cls'><option>TYCS</option><option>TYAIML</option><option>TE-A</option></select><br><br>
        <button onclick="fetch('/google_complete_register',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:'{email}',name:'{name}',roll:document.getElementById('roll').value,class:document.getElementById('cls').value}})}}).then(r=>r.json()).then(d=>location.href=d.redirect)">Submit</button>
        </body></html>
        """

@app.route('/login', methods=['POST'])
def login():
    try:
        role=request.form.get('role','teacher')
        uid=request.form.get('id','').strip().lower()
        pwd=request.form.get('password','').strip()
        if role=='teacher':
            if uid=='maths' and pwd=='1234':
                session['teacher']=True
                return redirect('/teacher_dashboard')
            return f"Invalid Teacher {uid}/{pwd}. Use maths/1234 <a href='/'>Back</a>"
        else:
            if not uid:
                return "Enter Roll <a href='/'>Back</a>"
            con=sqlite3.connect(DB)
            c=con.cursor()
            c.execute("SELECT roll,name,class FROM students WHERE roll=?", (uid,))
            row=c.fetchone()
            con.close()
            if row:
                session['student_roll']=row[0]
                session['student_name']=row[1]
                session['student_class']=row[2]
                return redirect('/student_dashboard')
            return f"Roll {uid} not found. Teacher must Add Student Manually first. <a href='/'>Back</a>"
    except Exception as ex:
        return f"Error {ex} <a href='/'>Back</a>"

@app.route('/google_login', methods=['POST'])
def google_login():
    try:
        data=request.get_json()
        role=data.get('role','student')
        email=data.get('email')
        name=data.get('name')
        if role=='teacher':
            session['teacher']=True
            return jsonify({"redirect":"/teacher_dashboard"})
        con=sqlite3.connect(DB)
        c=con.cursor()
        c.execute("SELECT roll,name,class FROM students WHERE email=?", (email,))
        row=c.fetchone()
        con.close()
        if row:
            session['student_roll']=row[0]
            session['student_name']=row[1]
            session['student_class']=row[2]
            return jsonify({"redirect":"/student_dashboard"})
        return jsonify({"need_details":True, "email":email, "name":name})
    except Exception as e:
        print(e)
        return jsonify({"redirect":"/"})

@app.route('/google_complete_register', methods=['POST'])
def google_complete():
    data=request.get_json()
    email=data.get('email')
    name=data.get('name')
    roll=str(data.get('roll')).strip()
    sclass=data.get('class','TYCS')
    con=sqlite3.connect(DB)
    c=con.cursor()
    c.execute("INSERT OR REPLACE INTO students (roll,name,class,email) VALUES (?,?,?,?)",(roll,name,sclass,email))
    con.commit()
    con.close()
    session['student_roll']=roll
    session['student_name']=name
    session['student_class']=sclass
    return jsonify({"redirect":"/student_dashboard"})

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if not session.get('teacher'):
        return redirect('/')
    con=sqlite3.connect(DB)
    c=con.cursor()
    c.execute("SELECT roll,name,class,email FROM students")
    students=c.fetchall()
    c.execute("SELECT roll,name,class,date,time,subject FROM attendance ORDER BY id DESC LIMIT 100")
    att=c.fetchall()
    con.close()
    return render_template('teacher_dashboard.html', students=students, attendance=att)

@app.route('/student_dashboard')
def student_dashboard():
    if not session.get('student_roll'):
        return redirect('/')
    return render_template('student_dashboard.html', roll=session.get('student_roll'), name=session.get('student_name'), sclass=session.get('student_class'))
    @app.route('/student_dashboard')
def student_dashboard():
    if not session.get('student_roll'):
        return redirect('/')
    roll=session.get('student_roll')
    con=sqlite3.connect(DB)
    c=con.cursor()
    c.execute("SELECT date,time,subject FROM attendance WHERE roll=? ORDER BY id DESC", (roll,))
    my_att=c.fetchall()
    con.close()
    return render_template('student_dashboard.html', roll=roll, name=session.get('student_name'), sclass=session.get('student_class'), attendance=my_att)

@app.route('/mark_attendance', methods=['POST'])
def mark_att():
    try:
        data=request.get_json() or {}
        roll=session.get('student_roll')
        if not roll:
            return jsonify({"ok":False})
        con=sqlite3.connect(DB)
        c=con.cursor()
        now=datetime.now()
        today=now.strftime("%Y-%m-%d")
        c.execute("SELECT id FROM attendance WHERE roll=? AND date=?", (roll,today))
        if c.fetchone():
            con.close()
            return jsonify({"ok":False, "msg":"Already marked"})
        c.execute("INSERT INTO attendance (roll,name,class,date,time,lat,lon,subject) VALUES (?,?,?,?,?,?,?,?)",(roll, session.get('student_name'), session.get('student_class'), today, now.strftime("%H:%M:%S"), data.get('lat'), data.get('lon'), data.get('sub','maths')))
        con.commit()
        con.close()
        return jsonify({"ok":True})
    except Exception as e:
        print(e)
        return jsonify({"ok":False})

@app.route('/add_student', methods=['POST'])
def add_student():
    if not session.get('teacher'):
        return redirect('/')
    roll=request.form.get('roll','').strip()
    name=request.form.get('name','').strip()
    sclass=request.form.get('class','TYCS')
    email=request.form.get('email','manual')
    if roll and name:
        con=sqlite3.connect(DB)
        c=con.cursor()
        c.execute("INSERT OR REPLACE INTO students (roll,name,class,email) VALUES (?,?,?,?)",(roll,name,sclass,email))
        con.commit()
        con.close()
    return redirect('/teacher_dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=10000)
