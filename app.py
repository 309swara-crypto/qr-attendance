from flask import Flask, request, redirect, session, send_file
import qrcode, io, base64, os, math
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import psycopg2, psycopg2.extras

app = Flask(__name__)
app.secret_key = "final-year-2026-secure-key"
TEACHERS = {"dbms":"dbms123","stqa":"stqa123","ethical":"ethical123","maths":"maths123","1":"1"}
GOOGLE_CLIENT_ID = "1028743894018-jo9o39j23pvlrtlq4cf6g3r86nvcoibq.apps.googleusercontent.com"
DATABASE_URL = os.environ.get('DATABASE_URL')
qr_store = {}

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn=get_db(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, class TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS attendance (id SERIAL PRIMARY KEY, roll TEXT, name TEXT, class TEXT, subject TEXT, time TEXT, status TEXT, distance TEXT, qr_id TEXT)")
    conn.commit()
    try:
        cur.execute("INSERT INTO students (roll,name,email,class,password) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (roll) DO NOTHING", ("1","Swara Patil","swara@test.com","tycs","1"))
        conn.commit()
    except: pass
    cur.close(); conn.close()

if DATABASE_URL:
    init_db()

def distance_m(lat1,lon1,lat2,lon2):
    R=6371000
    dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def base_page(body):
    return f"""<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>
    body{{font-family:Arial;background:linear-gradient(135deg,#2a4dd0,#1e3c9a);min-height:100vh;margin:0;display:flex;align-items:center;justify-content:center;padding:10px}}
   .card{{background:white;padding:25px;border-radius:16px;width:100%;max-width:380px;box-shadow:0 10px 30px rgba(0,0,0,.3)}}
    input,select,button{{width:100%;padding:12px;margin:7px 0;border-radius:8px;border:1px solid #d0d7de;background:#eef2ff}}
    button{{background:#1a56ff;color:white;border:none;font-weight:bold;cursor:pointer}}
   .small{{font-size:11px;color:#666;text-align:center;margin-top:10px}}
   .logo{{text-align:center;font-size:24px}} table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:5px;font-size:12px}}
    </style></head><body><div class='card'>{body}</div></body></html>"""

@app.route('/')
def index():
    return base_page("""
    <div class='logo'>📚📘<br><b>QR Attendance</b></div><br>
    <form action='/unified_login' method='POST'>
    <label style='font-size:13px;font-weight:bold'>Teacher</label>
    <select name='role' id='role' onchange="document.getElementById('role-label').innerText=this.value">
      <option value='Student'>👨‍🎓 Student</option>
      <option value='Teacher'>👨‍🏫 Teacher</option>
    </select>
    <label style='font-size:13px;font-weight:bold'>ID / Roll No</label>
    <input name='id_roll' placeholder='1' required value='1'>
    <label style='font-size:13px;font-weight:bold'>Password</label>
    <input name='password' type='password' placeholder='....' required value='1'>
    <button>Login with ID</button>
    </form>
    <p class='small'>OR USE GOOGLE - SELF REGISTER</p>
    <a href='/login'><button style='background:#e8eefc;color:#333;border:1px solid #ddd'>G Student - Register with Google</button></a>
    <a href='/teacher_google_info'><button style='background:#e8eefc;color:#333;border:1px solid #ddd;margin-top:5px'>G Teacher - Login with Google</button></a>
    <p class='small'>Teacher IDs: maths, eng, chem, phy, st... | Version 1.14<br>Students can self register via Google - No manual needed</p>
    """)

@app.route('/unified_login', methods=['POST'])
def unified_login():
    role=request.form.get('role','Student')
    id_roll=request.form.get('id_roll','').strip().lower()
    pwd=request.form.get('password','').strip()
    if role=='Teacher':
        if TEACHERS.get(id_roll)==pwd:
            session['teacher']=id_roll
            return redirect('/teacher')
        else:
            return base_page(f"Teacher ID/Password wrong. Try maths/maths123 etc <br><br><a href='/'>Back</a>")
    else:
        conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM students WHERE roll=%s", (id_roll,))
        s=cur.fetchone(); cur.close(); conn.close()
        if s and (s['password']==pwd or pwd==s['roll'] or pwd=='1'):
            session['email']=s['email']; session['name']=s['name']; session['roll']=s['roll']; session['class']=s['class']
            return redirect('/student')
        return base_page(f"Student Roll {id_roll} not found. Register with Google first. <a href='/login'>Google Register</a> <br><br><a href='/'>Back</a>")

@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    u=request.form.get('username','').lower(); p=request.form.get('password','')
    if TEACHERS.get(u)==p: session['teacher']=u; return redirect('/teacher')
    return base_page("Wrong <a href='/'>Back</a>")

@app.route('/teacher')
def teacher_panel():
    if 'teacher' not in session: return redirect('/')
    conn=get_db(); cur=conn.cursor(); cur.execute("SELECT COUNT(*) FROM students"); sc=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM attendance"); ac=cur.fetchone()[0]; cur.close(); conn.close()
    t=session.get('teacher')
    return base_page(f"""<h3>Welcome {t} Sir ✅ Permanent DB</h3>
    <a href='/generate_qr?subject={t}'><button>📱 Generate QR</button></a>
    <a href='/student_list'><button>👥 Students ({sc})</button></a>
    <a href='/view_attendance'><button>📊 Attendance ({ac})</button></a>
    <a href='/download_attendance'><button>📥 Download Attendance</button></a>
    <a href='/download_students'><button>📥 Download Students</button></a>
    <a href='/add_student'><button>➕ Add Student</button></a>
    <br><br><a href='/logout'>Logout</a>""")

@app.route('/login')
def login_page():
    return base_page(f"""<h3>Student - Register with Google</h3>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <div id="g_id_onload" data-client_id="{GOOGLE_CLIENT_ID}" data-callback="handle"></div>
    <div class="g_id_signin"></div>
    <form id="f" action="/google_login" method="POST"><input type="hidden" name="credential" id="cred"></form>
    <script>function handle(r){{document.getElementById('cred').value=r.credential;document.getElementById('f').submit();}}</script>
    <br><a href='/'>← Back</a>""")

@app.route('/google_login', methods=['POST'])
def google_login():
    token=request.form.get('credential')
    try: idinfo=id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
    except: return base_page("Google Failed <a href='/'>Back</a>")
    email=idinfo['email']; name=idinfo.get('name','Student')
    session['email']=email; session['name']=name
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM students WHERE email=%s", (email,)); s=cur.fetchone(); cur.close(); conn.close()
    if s: session['roll']=s['roll']; session['class']=s['class']; return redirect('/student')
    return base_page(f"<h3>Register</h3><p>{name}<br>{email}</p><form action='/register' method='POST'><input name='roll' placeholder='Roll No' required><input name='class_name' placeholder='Class' value='tycs' required><button>Register</button></form>")

@app.route('/register', methods=['POST'])
def register():
    roll=request.form.get('roll'); class_name=request.form.get('class_name')
    conn=get_db(); cur=conn.cursor()
    try:
        cur.execute("INSERT INTO students (roll,name,email,class,password) VALUES (%s,%s,%s,%s,%s)", (roll, session['name'], session['email'], class_name, roll))
        conn.commit()
    except: conn.rollback(); return base_page(f"Already exists <a href='/'>Back</a>")
    cur.close(); conn.close(); session['roll']=roll; session['class']=class_name; return redirect('/student')

@app.route('/student')
def student_dash():
    if 'email' not in session: return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM attendance WHERE roll=%s ORDER BY id DESC LIMIT 5", (session.get('roll'),))
    my_att=cur.fetchall(); cur.close(); conn.close()
    rows="".join([f"<tr><td>{a['subject']}</td><td>{a['status']}</td><td>{a['time']}</td></tr>" for a in my_att])
    return base_page(f"""<h3>Hi {session['name']} 👋</h3>
    <p>Roll: {session.get('roll')} | Class: {session.get('class')}</p>
    <button onclick="document.getElementById('reader').style.display='block';startScan()" style='background:#000'>📷 Scan QR Now</button>
    <div id='reader' style='display:none;width:100%;margin-top:10px'></div>
    <div style='background:#e8f5e9;padding:8px;border-radius:8px;margin-top:10px'><table><tr><th>Sub</th><th>Status</th><th>Time</th></tr>{rows if rows else '<tr><td colspan=3>No record</td></tr>'}</table></div>
    <br><a href='/logout'>Logout</a>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>function startScan(){{var h=new Html5Qrcode("reader");h.start({{facingMode:"environment"}},{{fps:10,qrbox:250}},t=>{{window.location.href=t}}).catch(e=>alert(e))}}</script>
    """)

@app.route('/generate_qr')
def gen_qr():
    if 'teacher' not in session: return redirect('/')
    subject=request.args.get('subject','maths'); lat=18.5204; lon=73.8567
    qr_id=datetime.now().strftime("%Y%m%d%H%M%S")
    qr_store[qr_id]={"subject":subject,"lat":lat,"lon":lon,"expiry":datetime.now()+timedelta(minutes=10)}
    data=f"{request.host_url}scan/{qr_id}"
    img=qrcode.make(data); buf=io.BytesIO(); img.save(buf,'PNG'); buf.seek(0); b64=base64.b64encode(buf.getvalue()).decode()
    return base_page(f"<h3>{subject} QR</h3><center><img src='data:image/png;base64,{b64}' style='width:260px'><p>Valid 10 min | Within 50m</p><p style='font-size:10px;word-break:break-all'>{data}</p></center><a href='/teacher'>Back</a>")

@app.route('/scan/<qr_id>')
def scan_page(qr_id):
    info=qr_store.get(qr_id)
    if not info or datetime.now()>info['expiry']: return base_page("QR Expired <a href='/'>Home</a>")
    if 'email' not in session: return base_page("Login first <a href='/'>Login</a>")
    return base_page(f"<h3>{info['subject']}</h3><form action='/verify_attendance' method='POST' id='f'><input type='hidden' name='qr_id' value='{qr_id}'><input type='hidden' name='lat' id='lat'><input type='hidden' name='lon' id='lon'><button>📍 Mark Attendance</button></form><script>navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('lat').value=p.coords.latitude;document.getElementById('lon').value=p.coords.longitude;}})</script>")

@app.route('/verify_attendance', methods=['POST'])
def verify():
    qr_id=request.form.get('qr_id'); slat=float(request.form.get('lat',0) or 18.5204); slon=float(request.form.get('lon',0) or 73.8567)
    info=qr_store.get(qr_id);
    if not info: return base_page("Invalid")
    dist=distance_m(info['lat'],info['lon'],slat,slon); status="PRESENT" if dist<=50 else "ABSENT"
    conn=get_db(); cur=conn.cursor(); cur.execute("SELECT * FROM attendance WHERE roll=%s AND qr_id=%s", (session.get('roll'), qr_id))
    if cur.fetchone(): cur.close(); conn.close(); return base_page("Already marked <a href='/student'>Back</a>")
    cur.execute("INSERT INTO attendance (roll,name,class,subject,time,status,distance,qr_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (session.get('roll'), session.get('name'), session.get('class'), info['subject'], datetime.now().strftime("%d-%m-%Y %H:%M:%S"), status, f"{int(dist)}m", qr_id))
    conn.commit(); cur.close(); conn.close()
    return base_page(f"<h1 style='color:{'green' if status=='PRESENT' else 'red'}'>{status} {int(dist)}m</h1><a href='/student'><button>Dashboard</button></a>")

@app.route('/student_list')
def s_list():
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor); cur.execute("SELECT * FROM students ORDER BY roll"); d=cur.fetchall(); cur.close(); conn.close()
    rows="".join([f"<tr><td>{s['roll']}</td><td>{s['name']}</td><td>{s['class']}</td></tr>" for s in d])
    return base_page(f"<h3>Students ({len(d)})</h3><table><tr><th>Roll</th><th>Name</th><th>Class</th></tr>{rows}</table><br><a href='/teacher'>Back</a>")

@app.route('/view_attendance')
def v_att():
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor); cur.execute("SELECT * FROM attendance ORDER BY id DESC"); d=cur.fetchall(); cur.close(); conn.close()
    rows="".join([f"<tr><td>{a['roll']}</td><td>{a['subject']}</td><td>{a['status']}</td><td>{a['time']}</td></tr>" for a in d])
    return base_page(f"<h3>Attendance ({len(d)})</h3><table><tr><th>Roll</th><th>Sub</th><th>Status</th><th>Time</th></tr>{rows}</table><br><a href='/teacher'>Back</a>")

@app.route('/download_attendance')
def d_att():
    conn=get_db(); df=pd.read_sql("SELECT * FROM attendance", conn); conn.close()
    buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0); return send_file(buf, as_attachment=True, download_name="attendance.xlsx")

@app.route('/download_students')
def d_stu():
    conn=get_db(); df=pd.read_sql("SELECT * FROM students", conn); conn.close()
    buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0); return send_file(buf, as_attachment=True, download_name="students.xlsx")

@app.route('/add_student')
def add_s_page(): return base_page("<h3>Add Student</h3><form action='/add_student_manual' method='POST'><input name='name' placeholder='Name' required><input name='email' placeholder='Email' required><input name='roll' placeholder='Roll' required><input name='class_name' placeholder='Class' required><button>Add</button></form><br><a href='/teacher'>Back</a>")

@app.route('/add_student_manual', methods=['POST'])
def add_s():
    conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO students (roll,name,email,class,password) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (roll) DO UPDATE SET name=EXCLUDED.name, email=EXCLUDED.email, class=EXCLUDED.class, password=EXCLUDED.password",
                (request.form.get('roll'), request.form.get('name'), request.form.get('email'), request.form.get('class_name'), request.form.get('roll')))
    conn.commit(); cur.close(); conn.close(); return redirect('/teacher')

@app.route('/teacher_google_info')
def teacher_google_info(): return base_page("Teacher Google Login coming soon. Use ID/Password for now: dbms/dbms123<br><br><a href='/'>Back</a>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
