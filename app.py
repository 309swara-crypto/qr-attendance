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

students = []
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
    <style>body{{font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;margin:0;display:flex;align-items:center;justify-content:center}}
   .card{{background:white;padding:25px;border-radius:15px;width:90%;max-width:500px;box-shadow:0 10px 30px rgba(0,0,0,.2)}}
    input,select,button{{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #ddd}}
    button{{background:#667eea;color:white;border:none;font-weight:bold;cursor:pointer}}
   .grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} a{{text-decoration:none;color:#667eea}}</style>
    </head><body><div class='card'>{body}</div></body></html>"""

@app.route('/')
def index():
    return base_page("""
    <h2>🎓 QR Attendance</h2>
    <form action='/teacher_login' method='POST'>
    <input name='username' placeholder='Teacher ID (dbms/stqa/maths/ethical)' required>
    <input name='password' type='password' placeholder='Password (dbms123 etc)' required>
    <button>Teacher Login</button></form><hr>
    <a href='/login'><button style='background:#34a853'>👨‍🎓 Student Login with Google</button></a>
    """)

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
    <h3>Welcome {t} Sir</h3><div class='grid'>
    <a href='/generate_qr?subject={t} TYCS'><button>📱 Generate QR</button></a>
    <a href='/student_list'><button>👥 Student List</button></a>
    <a href='/view_attendance'><button>📊 View Attendance</button></a>
    <a href='/download_attendance'><button>📥 Download Attendance Excel</button></a>
    <a href='/download_students'><button>📥 Download Students Excel</button></a>
    <a href='/add_student'><button>➕ Add Student</button></a>
    </div><br><a href='/logout'>Logout</a>""")

@app.route('/login')
def login_page():
    return base_page(f"""
    <h3>Student Login</h3>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <div id="g_id_onload" data-client_id="{GOOGLE_CLIENT_ID}" data-callback="handle"></div>
    <div class="g_id_signin"></div>
    <form id="f" action="/google_login" method="POST"><input type="hidden" name="credential" id="cred"></form>
    <script>function handle(r){{document.getElementById('cred').value=r.credential;document.getElementById('f').submit();}}</script>
    """)

@app.route('/google_login', methods=['POST'])
def google_login():
    token=request.form.get('credential')
    try:
        idinfo=id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
    except: return "Google Auth Failed - Check Client ID in Cloud Console"
    email=idinfo['email']; name=idinfo.get('name','Student')
    session['email']=email; session['name']=name
    for s in students:
        if s['email']==email: session['roll']=s['roll']; session['class']=s['class']; return redirect('/student')
    return base_page(f"<h3>Register</h3><p>{name} - {email}</p><form action='/register' method='POST'><input name='roll' placeholder='Roll No' required><input name='class_name' placeholder='Class TYCS' required><button>Register</button></form>")

@app.route('/register', methods=['POST'])
def register():
    roll=request.form.get('roll'); class_name=request.form.get('class_name')
    students.append({"name":session['name'],"email":session['email'],"roll":roll,"class":class_name})
    session['roll']=roll; session['class']=class_name; return redirect('/student')

@app.route('/student')
def student_dash():
    if 'email' not in session: return redirect('/')
    return base_page(f"<h3>Hi {session['name']}</h3><p>Roll: {session.get('roll')} | {session.get('class')}</p><p>Go to Teacher's QR to Scan</p><a href='/logout'>Logout</a>")

@app.route('/generate_qr')
def gen_qr():
    subject=request.args.get('subject','maths - TYCS')
    lat=float(request.args.get('lat',18.5204)); lon=float(request.args.get('lon',73.8567))
    qr_id=datetime.now().strftime("%Y%m%d%H%M%S")
    qr_store[qr_id]={"subject":subject,"lat":lat,"lon":lon,"expiry":datetime.now()+timedelta(minutes=10)}
    data=f"{request.host_url}scan/{qr_id}"
    img=qrcode.make(data); buf=io.BytesIO(); img.save(buf,'PNG'); buf.seek(0)
    b64=base64.b64encode(buf.getvalue()).decode()
    return base_page(f"<h3>{subject}</h3><img src='data:image/png;base64,{b64}' style='width:250px'><p>⏱️ Valid 10 mins</p><p>📍 Location Locked: {lat},{lon}</p><a href='/teacher'>Back</a>")

@app.route('/scan/<qr_id>')
def scan_page(qr_id):
    info=qr_store.get(qr_id)
    if not info or datetime.now()>info['expiry']: return base_page("QR Expired - Ask Teacher for new QR")
    return base_page(f"<h3>Scan for {info['subject']}</h3><form action='/verify_attendance' method='POST' onsubmit='return getLoc()'><input type='hidden' name='qr_id' value='{qr_id}'><input type='hidden' name='lat' id='lat'><input type='hidden' name='lon' id='lon'><button>✅ Mark Present</button></form><script>function getLoc(){{navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('lat').value=p.coords.latitude;document.getElementById('lon').value=p.coords.longitude;document.forms[0].submit();}});return false;}}</script>")

@app.route('/verify_attendance', methods=['POST'])
def verify():
    qr_id=request.form.get('qr_id'); slat=float(request.form.get('lat',0)); slon=float(request.form.get('lon',0))
    info=qr_store.get(qr_id)
    if not info: return "QR Invalid"
    dist=distance_m(info['lat'],info['lon'],slat,slon)
    status="PRESENT" if dist<=50 else "ABSENT"
    attendance.append({"roll":session.get('roll'),"name":session.get('name'),"class":session.get('class'),"subject":info['subject'],"time":datetime.now().strftime("%d-%m-%Y %H:%M:%S"),"status":status,"distance":f"{int(dist)}m"})
    if dist<=50: return base_page(f"<h1>✅ PRESENT {int(dist)}m</h1><p>Within 50m</p><a href='/student'>Back</a>")
    else: return base_page(f"<h1>❌ ABSENT {int(dist)}m Too Far</h1><p>Must be within 50m</p><a href='/student'>Back</a>")

@app.route('/student_list')
def s_list():
    rows="".join([f"<tr><td>{s['roll']}</td><td>{s['name']}</td><td>{s['class']}</td></tr>" for s in students])
    return base_page(f"<h3>Students</h3><table border=1 width=100%>{rows}</table><br><a href='/teacher'>Back</a>")

@app.route('/view_attendance')
def v_att():
    rows="".join([f"<tr><td>{a['roll']}</td><td>{a['name']}</td><td>{a['status']}</td><td>{a['time']}</td></tr>" for a in attendance])
    return base_page(f"<h3>Attendance</h3><table border=1 width=100%>{rows}</table><br><a href='/teacher'>Back</a>")

@app.route('/download_attendance')
def d_att():
    df=pd.DataFrame(attendance); buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="attendance.xlsx")

@app.route('/download_students')
def d_stu():
    df=pd.DataFrame(students); buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="students.xlsx")

@app.route('/add_student')
def add_s_page():
    return base_page("<h3>Add Student</h3><form action='/add_student_manual' method='POST'><input name='name' placeholder='Name' required><input name='email' placeholder='Email' required><input name='roll' placeholder='Roll' required><input name='class_name' placeholder='Class' required><button>Add</button></form>")

@app.route('/add_student_manual', methods=['POST'])
def add_s():
    students.append({"name":request.form.get('name'),"email":request.form.get('email'),"roll":request.form.get('roll'),"class":request.form.get('class_name')})
    return redirect('/teacher')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
