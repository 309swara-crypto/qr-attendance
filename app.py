from flask import Flask, request, redirect, session, render_template, send_file
import qrcode, io, base64, os, math
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import psycopg2

app = Flask(__name__)
app.secret_key = "final-year-2026-swara-qr"
TEACHERS = {"dbms":"dbms123","stqa":"stqa123","ethical":"ethical123","maths":"maths123","atqa":"atqa123","1":"1"}
GOOGLE_CLIENT_ID = "1028743894018-jo9o39j23pvlrtlq4cf6g3r86nvcoibq.apps.googleusercontent.com"
DATABASE_URL = os.environ.get('DATABASE_URL')
qr_store = {}

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, email TEXT, class TEXT, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS attendance (id SERIAL PRIMARY KEY, roll TEXT, name TEXT, class TEXT, subject TEXT, time TEXT, status TEXT, distance TEXT, qr_id TEXT)")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print("INIT ERROR", e)

if DATABASE_URL:
    init_db()

def dist_m(a,b,c,d):
    R=6371000
    try:
        dlat=math.radians(c-a); dlon=math.radians(d-b)
        x=math.sin(dlat/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(dlon/2)**2
        return R*2*math.atan2(math.sqrt(x),math.sqrt(1-x))
    except:
        return 0

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/teacher')
def teacher_page():
    if 'teacher' not in session:
        return redirect('/')
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("SELECT COUNT(*) FROM students"); sc=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM attendance"); ac=cur.fetchone()[0]
        cur.execute("SELECT roll,name,email,class FROM students ORDER BY roll DESC LIMIT 30"); students=cur.fetchall()
        cur.close(); conn.close()
    except:
        sc=0; ac=0; students=[]
    return render_template('teacher_dashboard.html', teacher=session.get('teacher'), sc=sc, ac=ac, students=students)

@app.route('/add_student_manual', methods=['POST'])
def add_manual():
    if 'teacher' not in session:
        return redirect('/')
    roll=request.form.get('roll','').strip()
    name=request.form.get('name','').strip()
    class_name=request.form.get('class_name','').strip() or "tycs"
    if not roll or not name:
        return "Roll Name required <a href='/teacher'>Back</a>"
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("DELETE FROM students WHERE roll=%s", (roll,))
        conn.commit()
        cur.execute("INSERT INTO students (roll,name,email,class,password) VALUES (%s,%s,%s,%s,%s)", (roll,name,f"{roll}@manual.com",class_name,roll))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        return f"Error: {e} <a href='/teacher'>Back</a>"
    return redirect('/teacher')

@app.route('/reset_db')
def reset_db():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("DROP TABLE IF EXISTS attendance"); cur.execute("DROP TABLE IF EXISTS students"); conn.commit()
        cur.execute("CREATE TABLE students (roll TEXT PRIMARY KEY, name TEXT, email TEXT, class TEXT, password TEXT)")
        cur.execute("CREATE TABLE attendance (id SERIAL PRIMARY KEY, roll TEXT, name TEXT, class TEXT, subject TEXT, time TEXT, status TEXT, distance TEXT, qr_id TEXT)")
        conn.commit(); cur.close(); conn.close()
        return "DB RESET DONE - <a href='/teacher'>Go Back</a>"
    except Exception as e:
        return f"Reset Error: {e}"

@app.route('/student')
def student_page():
    if 'roll' not in session and 'email' not in session:
        return redirect('/')
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("SELECT roll,name,class,subject,time,status,distance,qr_id FROM attendance WHERE roll=%s ORDER BY id DESC", (session.get('roll'),))
        attendance=cur.fetchall(); cur.close(); conn.close()
    except:
        attendance=[]
    return render_template('student_dashboard.html', name=session.get('name','Student'), roll=session.get('roll',''), class_name=session.get('class','tycs'), attendance=attendance)

@app.route('/unified_login', methods=['POST'])
def unified_login():
    role=request.form.get('role'); id_roll=request.form.get('id_roll','').lower().strip(); password=request.form.get('password','').strip()
    if role=='Teacher':
        if TEACHERS.get(id_roll)==password:
            session['teacher']=id_roll; return redirect('/teacher')
        return "Wrong Teacher <a href='/'>Back</a>"
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT roll,name,email,class FROM students WHERE roll=%s", (id_roll,)); s=cur.fetchone(); cur.close(); conn.close()
        if s:
            session['roll']=s[0]; session['name']=s[1]; session['email']=s[2]; session['class']=s[3]; return redirect('/student')
    except Exception as e:
        print(e)
    return f"Roll {id_roll} not found. <a href='/'>Back</a>"

# LIVE LOCATION QR GENERATION
@app.route('/generate_qr')
def gen_qr():
    if 'teacher' not in session:
        return redirect('/')
    sub=request.args.get('subject','dbms')
    # TAKE REAL LIVE LOCATION FROM TEACHER PHONE
    t_lat = float(request.args.get('lat') or 18.5204)
    t_lon = float(request.args.get('lon') or 73.8567)
    qid=datetime.now().strftime("%Y%m%d%H%M%S")
    qr_store[qid]={"subject":sub,"lat":t_lat,"lon":t_lon,"expiry":datetime.now()+timedelta(minutes=10)}
    print(f"QR {qid} created at {t_lat},{t_lon} by {sub}")
    link=f"{request.host_url}scan/{qid}"; img=qrcode.make(link); b=io.BytesIO(); img.save(b,'PNG'); b.seek(0); b64=base64.b64encode(b.getvalue()).decode()
    return render_template('generate_qr.html', subject=sub, qr_b64=b64, qr_link=link, t_lat=t_lat, t_lon=t_lon)

@app.route('/scan/<qid>')
def scan(qid):
    info=qr_store.get(qid)
    if not info or datetime.now()>info['expiry']:
        return "QR Expired - Ask teacher for new QR <a href='/student'>Back</a>"
    return render_template('scan.html', subject=info['subject'], qr_id=qid)

@app.route('/verify_attendance', methods=['POST'])
def verify():
    qid=request.form.get('qr_id'); lat=float(request.form.get('lat') or 18.5204); lon=float(request.form.get('lon') or 73.8567)
    info=qr_store.get(qid)
    if not info:
        return "QR Expired <a href='/student'>Back</a>"
    d=dist_m(info['lat'],info['lon'],lat,lon)
    st="PRESENT" if d<=500 else "ABSENT"
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("SELECT id FROM attendance WHERE roll=%s AND qr_id=%s", (session.get('roll'),qid))
        if cur.fetchone():
            cur.close(); conn.close(); return "Already Marked <a href='/student'>Back</a>"
        cur.execute("INSERT INTO attendance (roll,name,class,subject,time,status,distance,qr_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (session.get('roll'),session.get('name'),session.get('class'),info['subject'],datetime.now().strftime("%d-%m-%Y %H:%M"),st,f"{int(d)}m",qid))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        return f"DB Error: {e} <a href='/student'>Back</a>"
    return render_template('verify.html', status=st, dist=int(d))

@app.route('/login')
def glogin():
    return render_template('google_login.html', client_id=GOOGLE_CLIENT_ID)

@app.route('/google_login', methods=['POST'])
def glog():
    try:
        tok=request.form.get('credential'); info=id_token.verify_oauth2_token(tok, grequests.Request(), GOOGLE_CLIENT_ID)
        session['email']=info['email']; session['name']=info.get('name','Student')
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT roll,name,email,class FROM students WHERE email=%s", (session['email'],)); s=cur.fetchone(); cur.close(); conn.close()
        if s:
            session['roll']=s[0]; session['class']=s[3]; return redirect('/student')
        return render_template('register.html', name=session['name'], email=session['email'])
    except Exception as e:
        return f"Google Error: {e}"

@app.route('/register', methods=['POST'])
def reg():
    try:
        conn=get_db(); cur=conn.cursor(); roll=request.form.get('roll'); class_name=request.form.get('class_name') or "tycs"
        cur.execute("DELETE FROM students WHERE roll=%s", (roll,)); conn.commit()
        cur.execute("INSERT INTO students (roll,name,email,class,password) VALUES (%s,%s,%s,%s,%s)", (roll,session.get('name'),session.get('email'),class_name,roll))
        conn.commit(); cur.close(); conn.close(); session['roll']=roll; session['class']=class_name; return redirect('/student')
    except Exception as e:
        return f"Register Error: {e}"

@app.route('/student_list')
def sl():
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT roll,name,email,class FROM students ORDER BY roll"); d=cur.fetchall(); cur.close(); conn.close()
    except:
        d=[]
    return render_template('student_list.html', students=d)

@app.route('/view_attendance')
def vl():
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT roll,name,class,subject,time,status,distance FROM attendance ORDER BY id DESC"); d=cur.fetchall(); cur.close(); conn.close()
    except:
        d=[]
    return render_template('view_attendance.html', attendance=d)

@app.route('/download_attendance')
def dl1():
    try:
        conn=get_db(); df=pd.read_sql("SELECT * FROM attendance",conn); conn.close(); b=io.BytesIO(); df.to_excel(b,index=False); b.seek(0)
        return send_file(b,as_attachment=True,download_name="attendance.xlsx")
    except Exception as e:
        return f"No data: {e}"

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
