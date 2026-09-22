from flask import Flask, request, redirect, session, render_template, send_file
import qrcode, io, base64, os, math
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import psycopg2, psycopg2.extras

app = Flask(__name__)
app.secret_key = "final-year-2026"
TEACHERS = {"dbms":"dbms123","stqa":"stqa123","ethical":"ethical123","maths":"maths123","1":"1"}
GOOGLE_CLIENT_ID = "1028743894018-jo9o39j23pvlrtlq4cf6g3r86nvcoibq.apps.googleusercontent.com"
DATABASE_URL = os.environ.get('DATABASE_URL')
qr_store = {}

def get_db(): return psycopg2.connect(DATABASE_URL, sslmode='require')
def init_db():
    c=get_db(); cur=c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, class TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS attendance (id SERIAL PRIMARY KEY, roll TEXT, name TEXT, class TEXT, subject TEXT, time TEXT, status TEXT, distance TEXT, qr_id TEXT)")
    c.commit()
    try: cur.execute("INSERT INTO students VALUES (%s,%s,%s,%s,%s) ON CONFLICT (roll) DO NOTHING", ("1","Swara Patil","swara@test.com","tycs","1")); c.commit()
    except: pass
    cur.close(); c.close()
if DATABASE_URL: init_db()

def dist_m(a,b,c,d):
    R=6371000; dlat=math.radians(c-a); dlon=math.radians(d-b)
    x=math.sin(dlat/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(x),math.sqrt(1-x))

@app.route('/')
def index(): return render_template('login.html')

@app.route('/teacher')
def teacher_page():
    if 'teacher' not in session: return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT COUNT(*) FROM students"); sc=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM attendance"); ac=cur.fetchone()[0]
    cur.execute("SELECT * FROM students ORDER BY roll"); students=cur.fetchall()
    cur.close(); conn.close()
    return render_template('teacher_dashboard.html', teacher=session['teacher'], sc=sc, ac=ac, students=students)

@app.route('/add_student_manual', methods=['POST'])
def add_manual():
    if 'teacher' not in session: return redirect('/')
    roll=request.form.get('roll').strip(); name=request.form.get('name').strip(); class_name=request.form.get('class_name').strip(); email=f"{roll}@manual.com"
    conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO students (roll,name,email,class,password) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (roll) DO UPDATE SET name=%s, class=%s", (roll,name,email,class_name,roll,name,class_name))
    conn.commit(); cur.close(); conn.close()
    return redirect('/teacher')

@app.route('/student')
def student_page():
    if 'email' not in session: return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM attendance WHERE roll=%s ORDER BY id DESC", (session.get('roll'),)); at=cur.fetchall()
    cur.close(); conn.close()
    return render_template('student_dashboard.html', name=session['name'], roll=session.get('roll'), class_name=session.get('class'), attendance=at)

@app.route('/unified_login', methods=['POST'])
def unified_login():
    role=request.form.get('role'); r=request.form.get('id_roll','').lower().strip(); p=request.form.get('password','').strip()
    if role=='Teacher':
        if TEACHERS.get(r)==p: session['teacher']=r; return redirect('/teacher')
        return "Wrong Password <a href='/'>Back</a>"
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor); cur.execute("SELECT * FROM students WHERE roll=%s",(r,)); s=cur.fetchone(); cur.close(); conn.close()
    if s: session['email']=s['email']; session['name']=s['name']; session['roll']=s['roll']; session['class']=s['class']; return redirect('/student')
    return f"Roll {r} not found <a href='/login'>Register</a>"

@app.route('/generate_qr')
def gen_qr():
    sub=request.args.get('subject','dbms'); qid=datetime.now().strftime("%Y%m%d%H%M%S"); qr_store[qid]={"subject":sub,"lat":18.5204,"lon":73.8567,"expiry":datetime.now()+timedelta(minutes=10)}
    link=f"{request.host_url}scan/{qid}"; img=qrcode.make(link); b=io.BytesIO(); img.save(b,'PNG'); b.seek(0); b64=base64.b64encode(b.getvalue()).decode()
    return render_template('generate_qr.html', subject=sub, qr_b64=b64, qr_link=link)

@app.route('/scan/<qid>')
def scan(qid):
    i=qr_store.get(qid)
    if not i or datetime.now()>i['expiry']: return "QR Expired"
    return render_template('scan.html', subject=i['subject'], qr_id=qid)

@app.route('/verify_attendance', methods=['POST'])
def verify():
    qid=request.form.get('qr_id'); lat=float(request.form.get('lat') or 18.5204); lon=float(request.form.get('lon') or 73.8567); info=qr_store.get(qid)
    d=dist_m(info['lat'],info['lon'],lat,lon); st="PRESENT" if d<=50 else "ABSENT"
    conn=get_db(); cur=conn.cursor(); cur.execute("SELECT * FROM attendance WHERE roll=%s AND qr_id=%s",(session.get('roll'),qid))
    if cur.fetchone(): cur.close(); conn.close(); return "Already Marked <a href='/student'>Back</a>"
    cur.execute("INSERT INTO attendance (roll,name,class,subject,time,status,distance,qr_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(session.get('roll'),session.get('name'),session.get('class'),info['subject'],datetime.now().strftime("%d-%m-%Y %H:%M"),st,f"{int(d)}m",qid)); conn.commit(); cur.close(); conn.close()
    return render_template('verify.html', status=st, dist=int(d))

@app.route('/login')
def glogin(): return render_template('google_login.html', client_id=GOOGLE_CLIENT_ID)

@app.route('/google_login', methods=['POST'])
def glog():
    tok=request.form.get('credential'); info=id_token.verify_oauth2_token(tok, grequests.Request(), GOOGLE_CLIENT_ID)
    session['email']=info['email']; session['name']=info.get('name','Student')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor); cur.execute("SELECT * FROM students WHERE email=%s",(session['email'],)); s=cur.fetchone(); cur.close(); conn.close()
    if s: session['roll']=s['roll']; session['class']=s['class']; return redirect('/student')
    return render_template('register.html', name=session['name'], email=session['email'])

@app.route('/register', methods=['POST'])
def reg():
    conn=get_db(); cur=conn.cursor(); cur.execute("INSERT INTO students VALUES (%s,%s,%s,%s,%s)",(request.form.get('roll'),session['name'],session['email'],request.form.get('class_name'),request.form.get('roll'))); conn.commit(); cur.close(); conn.close()
    session['roll']=request.form.get('roll'); session['class']=request.form.get('class_name'); return redirect('/student')

@app.route('/student_list')
def sl():
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor); cur.execute("SELECT * FROM students"); d=cur.fetchall(); cur.close(); conn.close()
    return render_template('student_list.html', students=d)

@app.route('/view_attendance')
def vl():
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor); cur.execute("SELECT * FROM attendance ORDER BY id DESC"); d=cur.fetchall(); cur.close(); conn.close()
    return render_template('view_attendance.html', attendance=d)

@app.route('/download_attendance')
def dl1():
    conn=get_db(); df=pd.read_sql("SELECT * FROM attendance",conn); conn.close(); b=io.BytesIO(); df.to_excel(b,index=False); b.seek(0); return send_file(b,as_attachment=True,download_name="attendance.xlsx")

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
