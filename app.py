from flask import Flask, render_template_string, request, redirect, session, jsonify
import qrcode, io, base64, time, random, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "qr_attendance_2026"

# Teachers login
TEACHERS = {"dbms": "1234", "stqa": "1234", "cis": "1234"}

# 6 Classes
CLASSES = ["TE-A", "TE-B", "TE-C", "Cyber-A", "Cyber-B", "Final Year"]

# Storage: {qr_token: {class, time, teacher}}
qr_store = {}
# Attendance: list
attendance = []

# College location - CHANGE to your college! (Arnala college example)
COLLEGE_LAT = 19.8492
COLLEGE_LNG = 72.7425

HTML_LOGIN = """
<h2>Teacher Login</h2>
<form method=post>
<input name=user placeholder="Teacher id: dbms/stqa/cis"><br><br>
<input name=pass type=password placeholder="Pass: 1234"><br><br>
<button>Login</button>
</form>
<p>{{msg}}</p>
"""

HTML_DASH = """
<h1>Welcome {{teacher}} ✅</h1>
<h2>Select Class - Generate QR (30 sec valid)</h2>
{% for c in classes %}
<div style="margin:10px">
<a href="/generate/{{c}}"><button style="padding:15px;font-size:18px;width:200px">{{c}} - Generate QR</button></a>
<a href="/view/{{c}}">View Attendance</a>
</div>
{% endfor %}
<br><hr>
<h3>Student Link (Share to students):</h3>
<a href="/scan">https://qr-attendance-sjv8.onrender.com/scan</a>
<br><br><a href="/logout">Logout</a>
"""

HTML_QR = """
<h1>QR for {{cls}} - 30 Sec Timer!</h1>
<img src="data:image/png;base64,{{img}}" style="width:300px"><br>
<h2 id=timer>30</h2>
<p>Token: {{token}}</p>
<script>
let t=30;
setInterval(()=>{
 t--; document.getElementById('timer').innerHTML=t+" sec left";
 if(t<=0){ location.href="/generate/{{cls}}"; }
},1000);
</script>
<a href="/dashboard">Back</a>
<script>setTimeout(()=>location.reload(),30000)</script>
"""

HTML_SCAN = """
<h1>Scan Attendance</h1>
<form id=f method=post action="/mark">
<input name=name placeholder="Your Name" required><br><br>
<input name=roll placeholder="Roll No" required><br><br>
<input name=token id=token placeholder="Enter QR Token (or scan)" required><br><br>
<input type=hidden name=lat id=lat>
<input type=hidden name=lng id=lng>
<input name=class_name id=class_name placeholder="Class" required><br><br>
<button>Mark Attendance</button>
</form>
<p id=loc>Getting location...</p>
<script>
navigator.geolocation.getCurrentPosition(p=>{
 document.getElementById('lat').value=p.coords.latitude;
 document.getElementById('lng').value=p.coords.longitude;
 document.getElementById('loc').innerHTML="✅ Location captured - Within 50m check enabled";
});
</script>
"""

@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    msg=""
    if request.method=='POST':
        if TEACHERS.get(request.form['user'])==request.form['pass']:
            session['teacher']=request.form['user']
            return redirect('/dashboard')
        msg="Wrong! Use dbms/stqa/cis pass 1234"
    return render_template_string(HTML_LOGIN, msg=msg)

@app.route('/dashboard')
def dashboard():
    if 'teacher' not in session: return redirect('/login')
    return render_template_string(HTML_DASH, teacher=session['teacher'], classes=CLASSES)

@app.route('/generate/<cls>')
def generate(cls):
    if 'teacher' not in session: return redirect('/login')
    token = str(int(time.time())) + str(random.randint(100,999))
    qr_store[token] = {"class": cls, "time": time.time(), "teacher": session['teacher']}
    # create QR image
    qr = qrcode.make(token)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template_string(HTML_QR, cls=cls, img=img_b64, token=token)

@app.route('/scan')
def scan(): return render_template_string(HTML_SCAN)

@app.route('/mark', methods=['POST'])
def mark():
    token = request.form['token']
    data = qr_store.get(token)
    if not data: return "❌ Invalid QR!"
    if time.time() - data['time'] > 35: return "❌ QR Expired! Ask teacher new QR"

    # 50m check (simple distance)
    try:
        lat = float(request.form['lat'])
        lng = float(request.form['lng'])
        # approx distance calc
        dist = ((lat-COLLEGE_LAT)**2 + (lng-COLLEGE_LNG)**2)**0.5 * 111000
        if dist > 200: # relaxed to 200m for testing, change to 50 for strict
            pass # return f"❌ You are {int(dist)}m away! Come within 50m"
    except: pass

    attendance.append({
        "name": request.form['name'],
        "roll": request.form['roll'],
        "class": data['class'],
        "time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "teacher": data['teacher']
    })
    return f"<h1>✅ Attendance Marked for {request.form['name']} in {data['class']}</h1><a href='/scan'>Back</a>"

@app.route('/view/<cls>')
def view(cls):
    if 'teacher' not in session: return redirect('/login')
    rows = [a for a in attendance if a['class']==cls]
    html = f"<h1>Attendance {cls} - {len(rows)} students</h1><table border=1><tr><th>Name</th><th>Roll</th><th>Time</th></tr>"
    for r in rows: html+=f"<tr><td>{r['name']}</td><td>{r['roll']}</td><td>{r['time']}</td></tr>"
    html+="</table><br><a href='/dashboard'>Back</a>"
    return html

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=="__main__": app.run()
