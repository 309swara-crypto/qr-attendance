from flask import Flask, render_template_string, request, redirect, session, send_file
import qrcode, io, base64, time, random, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "final_pro_2026"

TEACHERS = {"dbms": "1234", "stqa": "1234", "cis": "1234"}
CLASSES = ["TE-A", "TE-B", "TE-C", "Cyber-A", "Cyber-B", "Final Year"]
qr_store = {}
attendance = []
students_db = {c: [] for c in CLASSES}

STYLE = """
<style>
body{font-family:'Segoe UI';background:#f4f6fb;margin:0}
.nav{background:#1a237e;color:white;padding:14px 22px;display:flex;justify-content:space-between;align-items:center}
.card{background:white;border-radius:14px;padding:20px;box-shadow:0 4px 15px rgba(0,0,0,.08);margin:15px auto;max-width:1050px}
.btn{padding:10px 14px;border:none;border-radius:8px;cursor:pointer;font-weight:600;margin:3px;font-size:13px}
.btn-p{background:#1a237e;color:white}.btn-s{background:#2e7d32;color:white}.btn-o{background:#ef6c00;color:white}.btn-i{background:#0288d1;color:white}.btn-d{background:#e8eaf6;color:#1a237e}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:15px}
input,select{padding:11px;width:92%;border:1px solid #ddd;border-radius:8px;margin:6px 0}
table{width:100%;border-collapse:collapse}th{background:#1a237e;color:white;padding:10px}td{padding:9px;border-bottom:1px solid #eee}
.login-wrap{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin-top:40px}
.login-card{width:380px}
</style>
"""

# ---------- HOME SELECTION ----------
HOME = STYLE + """
<div class=nav><h3>🎓 QR Attendance System</h3><span>VIDYAVARDHINI COLLEGE</span></div>
<div style="text-align:center; padding:30px">
<h1>Welcome to Smart Attendance</h1>
<p>Select Login Type</p>
<div class=login-wrap>
<div class="card login-card">
<h2 style="color:#1a237e">👨‍🏫 Teacher Dashboard</h2>
<p style="color:#666">Manage classes, QR, students</p>
<a href=/login><button class="btn btn-p" style="width:100%; padding:14px">Teacher Login →</button></a>
<p style="font-size:12px; margin-top:15px; background:#e8eaf6; padding:8px; border-radius:8px">ID: dbms, stqa, cis<br>Pass: 1234</p>
</div>
<div class="card login-card">
<h2 style="color:#2e7d32">👨‍🎓 Student Dashboard</h2>
<p style="color:#666">Scan QR, View attendance</p>
<a href=/student_login><button class="btn btn-s" style="width:100%; padding:14px">Student Login →</button></a>
<p style="font-size:12px; margin-top:15px; background:#e8f5e9; padding:8px; border-radius:8px">Login with Roll No<br>Check your records</p>
</div>
</div>
</div>
"""

@app.route('/')
def home(): return render_template_string(HOME)

# ---------- TEACHER LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    msg=""
    if request.method=='POST':
        if TEACHERS.get(request.form['user'])==request.form['pass']:
            session['teacher']=request.form['user']; return redirect('/dashboard')
        msg="Invalid Login"
    return render_template_string(STYLE+f"""
<div class=nav><h3>Teacher Login</h3><a href=/ style="color:white">Home</a></div>
<div class=card style="max-width:400px; margin-top:50px; text-align:center">
<h2>Teacher Login</h2>
<form method=post>
<input name=user placeholder="dbms / stqa / cis" required><br><br>
<input name=pass type=password placeholder="1234" required><br><br>
<button class="btn btn-p" style="width:95%">Login</button>
</form><p style="color:red">{msg}</p></div>
""")

@app.route('/dashboard')
def dashboard():
    if 'teacher' not in session: return redirect('/login')
    counts={c:len(students_db[c]) for c in CLASSES}
    html=STYLE+f"<div class=nav><h3>Teacher: {session['teacher'].upper()}</h3><div><a href=/ style='color:white; margin-right:15px'>Home</a><a href=/logout style='color:white'>Logout</a></div></div><div class=card><h2>Teacher Dashboard - 6 Classes</h2><div class=grid>"
    for c in CLASSES:
        html+=f"""
<div class=card style="margin:0; border-left:5px solid #1a237e">
<h3>{c} <span style="font-size:11px; background:#e8f5e9; padding:4px 8px; border-radius:10px">{counts[c]} Students</span></h3>
<a href="/generate/{c}"><button class="btn btn-p" style="width:100%">📱 Generate QR</button></a>
<div style="display:flex; flex-wrap:wrap; margin-top:5px">
<a href="/view_students/{c}" style="flex:1"><button class="btn btn-d" style="width:95%">👁 View Student</button></a>
<a href="/add_student/{c}" style="flex:1"><button class="btn btn-s" style="width:95%">➕ Add Student</button></a>
</div>
<div style="display:flex; flex-wrap:wrap">
<a href="/excel/{c}" style="flex:1"><button class="btn btn-o" style="width:95%">📥 Excel</button></a>
<a href="/view/{c}" style="flex:1"><button class="btn btn-i" style="width:95%">📊 View Attendance</button></a>
</div>
</div>
"""
    html+=f"</div><hr><p><b>Share to Students:</b> <code>https://qr-attendance-sjv8.onrender.com/scan</code></p></div>"
    return html

@app.route('/generate/<cls>')
def generate(cls):
    if 'teacher' not in session: return redirect('/login')
    token=str(int(time.time()))[-6:]+str(random.randint(10,99))
    qr_store[token]={"class":cls,"time":time.time()}
    qr=qrcode.make(token); buf=io.BytesIO(); qr.save(buf, format='PNG')
    img=base64.b64encode(buf.getvalue()).decode()
    return render_template_string(STYLE+f"""
<div class=nav><h3>QR - {cls}</h3><a href=/dashboard style="color:white">Dashboard</a></div>
<div class=card style="text-align:center; max-width:450px"><h2>{cls} - Live QR</h2><img src="data:image/png;base64,{img}" style="width:280px; border:2px solid #1a237e; border-radius:12px"><h1 id=t style="color:red">30s</h1><p>Token: <b>{token}</b></p><p style="background:#fff3e0; padding:8px; border-radius:8px">Show this QR in projector - Expires in 30s</p>
<script>let t=30;setInterval(()=>{{t--;document.getElementById('t').innerHTML=t+'s LEFT'; if(t<=0) location.href='/generate/{cls}'}},1000);setTimeout(()=>location.reload(),30000)</script></div>
""")

@app.route('/add_student/<cls>', methods=['GET','POST'])
def add_student(cls):
    if 'teacher' not in session: return redirect('/login')
    if request.method=='POST':
        students_db[cls].append({"name":request.form['name'],"roll":request.form['roll']})
        return redirect(f'/view_students/{cls}')
    return render_template_string(STYLE+f"<div class=nav><h3>Add - {cls}</h3><a href=/dashboard style='color:white'>Back</a></div><div class=card style='max-width:400px'><form method=post><input name=name placeholder='Student Name' required><br><br><input name=roll placeholder='Roll No (e.g. 309)' required><br><br><button class='btn btn-s' style='width:95%'>Add</button></form></div>")

@app.route('/view_students/<cls>')
def view_students(cls):
    if 'teacher' not in session: return redirect('/login')
    html=STYLE+f"<div class=nav><h3>{cls} Students - {len(students_db[cls])}</h3><a href=/dashboard style='color:white'>Back</a></div><div class=card><a href='/add_student/{cls}'><button class='btn btn-s'>➕ Add Student</button></a> <a href='/excel/{cls}'><button class='btn btn-o'>📥 Excel Download</button></a><br><br><table><tr><th>#</th><th>Name</th><th>Roll</th></tr>"
    for i,r in enumerate(students_db[cls],1): html+=f"<tr><td>{i}</td><td>{r['name']}</td><td>{r['roll']}</td></tr>"
    return html+"</table></div>"

@app.route('/excel/<cls>')
def excel(cls):
    if 'teacher' not in session: return redirect('/login')
    output=io.StringIO(); w=csv.writer(output)
    w.writerow([f'Class: {cls}']); w.writerow(['Name','Roll','Last Attendance','Status'])
    for s in students_db[cls]:
        atts=[a for a in attendance if a['class']==cls and a['roll']==s['roll']]
        w.writerow([s['name'],s['roll'],atts[-1]['time'] if atts else '','Present' if atts else 'Absent'])
    mem=io.BytesIO(); mem.write(output.getvalue().encode()); mem.seek(0)
    return send_file(mem, download_name=f"{cls}_attendance.csv", as_attachment=True)

@app.route('/view/<cls>')
def view(cls):
    if 'teacher' not in session: return redirect('/login')
    rows=[a for a in attendance if a['class']==cls]
    html=STYLE+f"<div class=nav><h3>{cls} Attendance - {len(rows)}</h3><a href=/dashboard style='color:white'>Back</a></div><div class=card><table><tr><th>Name</th><th>Roll</th><th>Time</th></tr>"
    for r in rows: html+=f"<tr><td>{r['name']}</td><td>{r['roll']}</td><td>{r['time']}</td></tr>"
    return html+"</table></div>"

# ---------- STUDENT DASHBOARD ----------
@app.route('/student_login', methods=['GET','POST'])
def student_login():
    if request.method=='POST':
        session['student_roll']=request.form['roll']
        session['student_name']=request.form['name']
        return redirect('/student_dashboard')
    return render_template_string(STYLE+"""
<div class=nav><h3>Student Login</h3><a href=/ style="color:white">Home</a></div>
<div class=card style="max-width:400px; margin-top:40px">
<h2>👨‍🎓 Student Dashboard</h2>
<form method=post>
<input name=name placeholder='Your Full Name' required><br><br>
<input name=roll placeholder='Your Roll No' required><br><br>
<button class="btn btn-s" style="width:95%">Login to Dashboard</button>
</form>
</div>
""")

@app.route('/student_dashboard')
def student_dashboard():
    if 'student_roll' not in session: return redirect('/student_login')
    roll=session['student_roll']; name=session['student_name']
    my_att=[a for a in attendance if a['roll']==roll]
    html=STYLE+f"<div class=nav><h3>Student: {name} ({roll})</h3><div><a href=/ style='color:white; margin-right:10px'>Home</a><a href=/student_logout style='color:white'>Logout</a></div></div><div class=card><h2>Welcome {name}!</h2><div style='display:flex; gap:10px; flex-wrap:wrap'><a href=/scan><button class='btn btn-p'>📱 Scan QR - Mark Attendance</button></a><a href='/view_my'><button class='btn btn-i'>📊 View My Attendance ({len(my_att)})</button></a></div><br><h3>My Attendance History</h3><table><tr><th>Class</th><th>Date Time</th><th>Status</th></tr>"
    for r in my_att: html+=f"<tr><td>{r['class']}</td><td>{r['time']}</td><td style='color:green'>Present</td></tr>"
    if not my_att: html+="<tr><td colspan=3>No attendance yet - Scan QR in class</td></tr>"
    return html+"</table></div>"

@app.route('/view_my')
def view_my():
    if 'student_roll' not in session: return redirect('/student_login')
    return redirect('/student_dashboard')

@app.route('/scan')
def scan():
    return render_template_string(STYLE+"""
<div class=nav><h3>Scan QR</h3><a href=/student_dashboard style="color:white">Dashboard</a></div>
<div class=card style="max-width:400px"><h3>Mark Attendance</h3>
<form method=post action="/mark">
<input name=name placeholder='Name' required><br><br>
<input name=roll placeholder='Roll No' required><br><br>
<input name=token placeholder='Enter Token from QR Screen' required><br><br>
<button class='btn btn-s' style="width:95%">Submit Attendance</button>
</form></div>
""")

@app.route('/mark', methods=['POST'])
def mark():
    token=request.form['token']; data=qr_store.get(token)
    if not data: return "<h1>❌ Invalid QR - Ask teacher for new QR</h1><a href=/scan>Try Again</a>"
    if time.time()-data['time']>35: return "<h1>❌ Expired - 30s over</h1><a href=/scan>Try Again</a>"
    attendance.append({"name":request.form['name'],"roll":request.form['roll'],"class":data['class'],"time":datetime.now().strftime("%d-%m-%Y %H:%M:%S")})
    return f"<div style='text-align:center; margin-top:60px; font-family:Arial'><h1 style='color:green'>✅ Attendance Marked!</h1><h2>{request.form['name']} - {data['class']}</h2><a href=/student_dashboard>Go to Dashboard</a></div>"

@app.route('/logout')
def logout(): session.clear(); return redirect('/')
@app.route('/student_logout')
def student_logout(): session.clear(); return redirect('/')

if __name__=="__main__": app.run()
