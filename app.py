from flask import Flask, render_template, request, redirect, session, send_file
import qrcode, io, base64, os, math
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

app = Flask(__name__)
app.secret_key = "final-year-2026"

TEACHERS = {"dbms":"dbms123","stqa":"stqa123","ethical":"ethical123","maths":"maths123"}
GOOGLE_CLIENT_ID = "1028743894018-jo9o39j23pvlrtlq4cf6g3r86nvcoibq.apps.googleusercontent.com"

students = []
attendance = []
qr_store = {}

def distance_m(lat1,lon1,lat2,lon2):
    R=6371000
    dlat=math.radians(lat2-lat1)
    dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    u=request.form.get('username','').lower()
    p=request.form.get('password','')
    if TEACHERS.get(u)==p:
        session['teacher']=u
        return redirect('/teacher')
    return "Wrong ID/Password"

@app.route('/teacher')
def teacher_panel():
    if 'teacher' not in session:
        return redirect('/')
    return render_template('teacher_dashboard.html', teacher=session.get('teacher'))

@app.route('/login')
def login_page():
    return render_template('login.html', client_id=GOOGLE_CLIENT_ID)

@app.route('/google_login', methods=['POST'])
def google_login():
    token=request.form.get('credential')
    idinfo=id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
    email=idinfo['email']
    name=idinfo.get('name','Student')
    session['email']=email
    session['name']=name
    for s in students:
        if s['email']==email:
            session['roll']=s['roll']
            session['class']=s['class']
            return redirect('/student')
    return render_template('register.html', name=name, email=email)

@app.route('/register', methods=['POST'])
def register():
    roll=request.form.get('roll')
    class_name=request.form.get('class_name')
    students.append({"name":session['name'],"email":session['email'],"roll":roll,"class":class_name})
    session['roll']=roll
    session['class']=class_name
    return redirect('/student')

@app.route('/student')
def student_dash():
    if 'email' not in session:
        return redirect('/')
    return render_template('student_dashboard.html', name=session['name'], roll=session.get('roll'), class_name=session.get('class'))

@app.route('/generate_qr')
def gen_qr():
    subject=request.args.get('subject','maths - TYCS')
    lat=float(request.args.get('lat',20.99))
    lon=float(request.args.get('lon',75.56))
    qr_id=datetime.now().strftime("%Y%m%d%H%M%S")
    qr_store[qr_id]={"subject":subject,"lat":lat,"lon":lon,"expiry":datetime.now()+timedelta(minutes=10)}
    data=f"{request.host_url}scan/{qr_id}"
    img=qrcode.make(data)
    buf=io.BytesIO()
    img.save(buf,'PNG')
    buf.seek(0)
    b64=base64.b64encode(buf.getvalue()).decode()
    return render_template('generate_qr.html', qr_code=b64, subject=subject, lat=lat, lon=lon)

@app.route('/scan/<qr_id>')
def scan_page(qr_id):
    info=qr_store.get(qr_id)
    if not info or datetime.now()>info['expiry']:
        return "QR Expired - Ask Teacher for new QR"
    return render_template('scan_qr.html', qr_id=qr_id, subject=info['subject'])

@app.route('/verify_attendance', methods=['POST'])
def verify():
    qr_id=request.form.get('qr_id')
    slat=float(request.form.get('lat',0))
    slon=float(request.form.get('lon',0))
    info=qr_store.get(qr_id)
    if not info:
        return "QR Invalid"
    dist=distance_m(info['lat'],info['lon'],slat,slon)
    status="PRESENT" if dist<=50 else "ABSENT - Too Far"
    attendance.append({"roll":session.get('roll'),"name":session.get('name'),"class":session.get('class'),"subject":info['subject'],"time":datetime.now().strftime("%d-%m-%Y %H:%M:%S"),"status":status,"distance":f"{int(dist)}m"})
    if dist<=50:
        return f"<h1>✅ PRESENT - {int(dist)}m Within 50m 🎉</h1><a href='/student'>Back</a>"
    else:
        return f"<h1>❌ ABSENT - Too Far {int(dist)}m Must be within 50m</h1><a href='/student'>Back</a>"

@app.route('/student_list')
def s_list():
    return render_template('student_list.html', students=students)

@app.route('/view_attendance')
def v_att():
    return render_template('attendance.html', attendance=attendance)

@app.route('/download_attendance')
def d_att():
    df=pd.DataFrame(attendance)
    buf=io.BytesIO()
    df.to_excel(buf,index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="attendance.xlsx")

@app.route('/download_students')
def d_stu():
    df=pd.DataFrame(students)
    buf=io.BytesIO()
    df.to_excel(buf,index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="students.xlsx")

@app.route('/add_student')
def add_s_page():
    return render_template('add_student.html')

@app.route('/add_student_manual', methods=['POST'])
def add_s():
    students.append({"name":request.form.get('name'),"email":request.form.get('email'),"roll":request.form.get('roll'),"class":request.form.get('class_name')})
    return redirect('/teacher')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
