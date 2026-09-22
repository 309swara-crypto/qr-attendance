from flask import Flask, request, redirect, session, send_file
import qrcode, io, base64, os, math
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

app = Flask(__name__)
app.secret_key = "final-year-2026-secure-key"

TEACHERS = {"dbms":"dbms123","stqa":"stqa123","ethical":"ethical123","maths":"maths123"}
GOOGLE_CLIENT_ID = "1028743894018-jo9o39j23pvlrtlq4cf6g3r86nvcoibq.apps.googleusercontent.com"

students = [{"name":"Swara Patil","email":"swara@test.com","roll":"1","class":"tycs","password":"1"}]
attendance = []
qr_store = {}

def distance_m(lat1,lon1,lat2,lon2):
    R=6371000
    dlat=math.radians(lat2-lat1)
    dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def base_page(body):
    return f"""
    <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>
    body{{font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;margin:0;display:flex;align-items:center;justify-content:center}}
    .card{{background:white;padding:25px;border-radius:15px;width:90%;max-width:550px;box-shadow:0 10px 30px rgba(0,0,0,.2)}}
    input,select,button{{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #ddd;box-sizing:border-box}}
    button{{background:#667eea;color:white;border:none;font-weight:bold;cursor:pointer}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} 
    a{{text-decoration:none;color:#667eea}}
    table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:8px;font-size:13px}}
    </style>
    </head><body><div class='card'>{body}</div></body></html>"""

@app.route('/')
def index():
    return base_page("""
    <h2>🎓 QR Attendance System</h2>
    <b>👨‍🏫 Teacher Login</b>
    <form action='/teacher_login' method='POST'>
    <input name='username' placeholder='Teacher ID (dbms/stqa/ethical/maths)' required>
    <input name='password' type='password' placeholder='Password' required>
    <button>Teacher Login</button></form><hr>
    <b>👨‍🎓 Student Login</b>
    <form action='/student_manual_login' method='POST'>
    <input name='roll' placeholder='Roll No (e.g. 1)' required>
    <input name='password' type='password' placeholder='Password = Roll No' required>
    <button style='background:#ff9800'>Manual Login</button></form>
    <p style='text-align:center'>OR</p>
    <a href='/login'><button style='background:#34a853'>Login with Google</button></a>
    """)

# --- TEACHER ---
@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    u=request.form.get('username','').lower(); p=request.form.get('password','')
    if TEACHERS.get(u)==p:
        session['teacher']=u; return redirect('/teacher')
    return base_page("Wrong ID/Password <a href='/'>Back</a>")

@app.route('/teacher')
def teacher_panel():
    if 'teacher' not in session: return redirect('/')
    t=session.get('teacher')
    return base_page(f"""
    <h3>Welcome {t} Sir</h3>
    <p>Today: {datetime.now().strftime('%d-%m-%Y')}</p>
    <div class='grid'>
    <a href='/generate_qr?subject={t} TYCS'><button>📱 Generate QR</button></a>
    <a href='/student_list'><button>👥 Students ({len(students)})</button></a>
    <a href='/view_attendance'><button>📊 Attendance ({len(attendance)})</button></a>
    <a href='/download_attendance'><button>📥 Attendance Excel</button></a>
    <a href='/download_students'><button>📥 Students Excel</button></a>
    <a href='/add_student'><button>➕ Add Student</button></a>
    </div><br><a href='/logout'>Logout</a>""")

# --- STUDENT MANUAL + GOOGLE ---
@app.route('/student_manual_login', methods=['POST'])
def student_manual_login():
    roll=request.form.get('roll'); pwd=request.form.get('password')
    for s in students:
        if s['roll']==roll and (s.get('password')==pwd or pwd==s['roll']):
            session['email']=s['email']; session['name']=s['name']; session['roll']=s['roll']; session['class']=s['class']
            return redirect('/student')
    return base_page(f"Student Roll {roll} not found. Please register via Google first or ask teacher to add you. <a href='/'>Back</a>")

@app.route('/login')
def login_page():
    return base_page(f"""
    <h3>Student Google Login</h3>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <div id="g_id_onload" data-client_id="{GOOGLE_CLIENT_ID}" data-callback="handle"></div>
    <div class="g_id_signin"></div>
    <form id="f" action="/google_login" method="POST"><input type="hidden" name="credential" id="cred"></form>
    <script>function handle(r){{document.getElementById('cred').value=r.credential;document.getElementById('f').submit();}}</script>
    <br><a href='/'>Manual Login</a>
    """)

@app.route('/google_login', methods=['POST'])
def google_login():
    token=request.form.get('credential')
    try:
        idinfo=id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
    except: return base_page("Google Auth Failed. Check Client ID <a href='/'>Back</a>")
    email=idinfo['email']; name=idinfo.get('name','Student')
    session['email']=email; session['name']=name
    for s in students:
        if s['email']==email: session['roll']=s['roll']; session['class']=s['class']; return redirect('/student')
    return base_page(f"<h3>New Student Register</h3><p>{name}<br>{email}</p><form action='/register' method='POST'><input name='roll' placeholder='Roll No' required><input name='class_name' placeholder='Class TYCS' value='tycs' required><button>Register & Login</button></form>")

@app.route('/register', methods=['POST'])
def register():
    roll=request.form.get('roll'); class_name=request.form.get('class_name')
    students.append({"name":session['name'],"email":session['email'],"roll":roll,"class":class_name,"password":roll})
    session['roll']=roll; session['class']=class_name; return redirect('/student')

# --- STUDENT DASHBOARD ---
@app.route('/student')
def student_dash():
    if 'email' not in session: return redirect('/')
    roll=session.get('roll')
    my_att=[a for a in attendance if a['roll']==roll]
    rows="".join([f"<tr><td>{a['subject']}</td><td>{a['status']}</td><td>{a['time']}</td><td>{a['distance']}</td></tr>" for a in my_att[-5:][::-1]])
    return base_page(f"""
    <h3>Hi {session['name']} 👋</h3>
    <p><b>Roll:</b> {session.get('roll')} | <b>Class:</b> {session.get('class')}<br>
    <b>Email:</b> {session.get('email')}</p><hr>
    <p>📱 Go to Teacher's QR and Scan to mark attendance</p>
    <div style='background:#e8f5e9;padding:10px;border-radius:8px'>
    <b>Your Recent Attendance ({len(my_att)})</b>
    <table><tr><th>Subject</th><th>Status</th><th>Time</th><th>Dist</th></tr>{rows if rows else '<tr><td colspan=4>No record yet</td></tr>'}</table>
    </div><br>
    <a href='/logout'><button style='background:#f44336'>Logout</button></a>
    """)

@app.route('/generate_qr')
def gen_qr():
    if 'teacher' not in session: return redirect('/')
    subject=request.args.get('subject','maths - TYCS')
    lat=float(request.args.get('lat',18.5204)); lon=float(request.args.get('lon',73.8567))
    qr_id=datetime.now().strftime("%Y%m%d%H%M%S")
    qr_store[qr_id]={"subject":subject,"lat":lat,"lon":lon,"expiry":datetime.now()+timedelta(minutes=10)}
    data=f"{request.host_url}scan/{qr_id}"
    img=qrcode.make(data); buf=io.BytesIO(); img.save(buf,'PNG'); buf.seek(0)
    b64=base64.b64encode(buf.getvalue()).decode()
    return base_page(f"<h3>{subject} - QR</h3><center><img src='data:image/png;base64,{b64}' style='width:280px;border:10px solid white;box-shadow:0 0 10px #ccc'><p>⏱️ Valid 10 mins</p><p>📍 Location Locked: {lat:.5f},{lon:.5f}<br>Students must be within 50m</p><p style='font-size:11px;word-break:break-all'>{data}</p></center><a href='/teacher'>Back to Dashboard</a>")

@app.route('/scan/<qr_id>')
def scan_page(qr_id):
    info=qr_store.get(qr_id)
    if not info or datetime.now()>info['expiry']: return base_page("❌ QR Expired - Ask Teacher for new QR <br><br><a href='/'>Home</a>")
    if 'email' not in session:
        return base_page(f"You must login as student first<br><br><a href='/login'><button>Student Login</button></a><br><a href='/'>Home</a>")
    return base_page(f"<h3>Mark Attendance</h3><p><b>{info['subject']}</b></p><p>Your location will be checked (must be within 50m)</p><form action='/verify_attendance' method='POST' id='myf'><input type='hidden' name='qr_id' value='{qr_id}'><input type='hidden' name='lat' id='lat'><input type='hidden' name='lon' id='lon'><button id='btn'>📍 Allow Location & Mark Present</button></form><script>document.getElementById('myf').onsubmit=function(e){{e.preventDefault();document.getElementById('btn').innerText='Getting location...';navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('lat').value=p.coords.latitude;document.getElementById('lon').value=p.coords.longitude;e.target.submit();}},err=>{{alert('Please allow location: '+err.message)}})}};</script>")

@app.route('/verify_attendance', methods=['POST'])
def verify():
    qr_id=request.form.get('qr_id'); slat=float(request.form.get('lat',0)); slon=float(request.form.get('lon',0))
    info=qr_store.get(qr_id)
    if not info: return base_page("QR Invalid <a href='/student'>Back</a>")
    dist=distance_m(info['lat'],info['lon'],slat,slon)
    status="PRESENT" if dist<=50 else "ABSENT"
    # prevent duplicate same QR
    for a in attendance:
        if a['roll']==session.get('roll') and a['subject']==info['subject'] and qr_id in a.get('qr_id',''):
            return base_page(f"Already marked as {a['status']} <a href='/student'>Back</a>")
    attendance.append({"roll":session.get('roll'),"name":session.get('name'),"class":session.get('class'),"subject":info['subject'],"time":datetime.now().strftime("%d-%m-%Y %H:%M:%S"),"status":status,"distance":f"{int(dist)}m","qr_id":qr_id})
    if dist<=50: return base_page(f"<h1 style='color:green'>✅ PRESENT</h1><p>Distance: {int(dist)}m (within 50m)</p><p>{info['subject']}</p><a href='/student'><button>Go to Dashboard</button></a>")
    else: return base_page(f"<h1 style='color:red'>❌ ABSENT</h1><p>Too far: {int(dist)}m > 50m</p><p>You must be in classroom</p><a href='/student'><button>Back</button></a>")

@app.route('/student_list')
def s_list():
    if 'teacher' not in session: return redirect('/')
    rows="".join([f"<tr><td>{s['roll']}</td><td>{s['name']}</td><td>{s['class']}</td><td>{s['email']}</td></tr>" for s in students])
    return base_page(f"<h3>Students List ({len(students)})</h3><table><tr><th>Roll</th><th>Name</th><th>Class</th><th>Email</th></tr>{rows}</table><br><a href='/teacher'>Back</a>")

@app.route('/view_attendance')
def v_att():
    if 'teacher' not in session: return redirect('/')
    rows="".join([f"<tr><td>{a['roll']}</td><td>{a['name']}</td><td>{a['subject']}</td><td>{a['status']}</td><td>{a['time']}</td><td>{a['distance']}</td></tr>" for a in attendance[::-1]])
    return base_page(f"<h3>All Attendance ({len(attendance)})</h3><table><tr><th>Roll</th><th>Name</th><th>Subject</th><th>Status</th><th>Time</th><th>Dist</th></tr>{rows if rows else '<tr><td colspan=6>No attendance yet</td></tr>'}</table><br><a href='/teacher'>Back</a>")

@app.route('/download_attendance')
def d_att():
    if 'teacher' not in session: return redirect('/')
    df=pd.DataFrame(attendance); buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="attendance.xlsx")

@app.route('/download_students')
def d_stu():
    if 'teacher' not in session: return redirect('/')
    df=pd.DataFrame(students); buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="students.xlsx")

@app.route('/add_student')
def add_s_page():
    if 'teacher' not in session: return redirect('/')
    return base_page("<h3>Add Student Manually</h3><form action='/add_student_manual' method='POST'><input name='name' placeholder='Name' required><input name='email' placeholder='Email' required><input name='roll' placeholder='Roll No' required><input name='class_name' placeholder='Class TYCS' required><input name='password' placeholder='Password (default = roll)'><button>Add Student</button></form><br><a href='/teacher'>Back</a>")

@app.route('/add_student_manual', methods=['POST'])
def add_s():
    if 'teacher' not in session: return redirect('/')
    pwd=request.form.get('password') or request.form.get('roll')
    students.append({"name":request.form.get('name'),"email":request.form.get('email'),"roll":request.form.get('roll'),"class":request.form.get('class_name'),"password":pwd})
    return redirect('/teacher')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
