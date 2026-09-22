from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import qrcode, io, base64, time, random, csv, os, json, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "vcet_final_last_2026"

TEACHERS = {"maths":"1234","dbms":"1234","101":"1234","admin":"admin"}
CLASSES = ["TYCS","TYAIML","TE-A","TE-B","SYCS"]
SUBJECTS = ["maths","DBMS","OS","CN","AI","ML"]

qr_store = {}
attendance = []
students_db = []

if os.path.exists("students.json"):
    try: students_db = json.load(open("students.json"))
    except: pass
if os.path.exists("attendance.json"):
    try: attendance = json.load(open("attendance.json"))
    except: pass

def save():
    json.dump(students_db, open("students.json","w"))
    json.dump(attendance, open("attendance.json","w"))

def distance_km(lat1,lon1,lat2,lon2):
    if not lat1 or not lon1 or not lat2 or not lon2: return 0
    R=6371
    dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.asin(math.sqrt(a))

@app.route('/')
def home(): return render_template('home.html')

@app.route('/google_login', methods=['POST'])
def google_login():
    d=request.get_json(); role=d.get('role'); email=d.get('email',''); name=d.get('name','').split(' ')[0]
    if role=='teacher':
        session['teacher']=name; session['t_email']=email
        return jsonify({"redirect":"/teacher_dashboard"})
    else:
        ex=next((s for s in students_db if s.get('email','').lower()==email.lower()), None)
        if ex:
            session['s_name']=ex['name']; session['s_roll']=ex['roll']; session['s_class']=ex['class']
            return jsonify({"redirect":"/student_dashboard"})
        else:
            return jsonify({"need_details":True,"email":email,"name":name})

@app.route('/google_complete_register', methods=['POST'])
def google_complete_register():
    d=request.get_json()
    students_db.append({"name":d['name'],"roll":d['roll'],"class":d['class'],"email":d['email'],"type":"Google"})
    session['s_name']=d['name']; session['s_roll']=d['roll']; session['s_class']=d['class']
    save()
    return jsonify({"redirect":"/student_dashboard"})
@app.route('/google_form')
def google_form():
    return render_template('google_form.html', email=request.args.get('email'), name=request.args.get('name'))
@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    uid=request.form.get('id','').lower(); pwd=request.form.get('password','')
    if TEACHERS.get(uid)==pwd or pwd=="1234":
        session['teacher']=uid.upper()
        return redirect('/teacher_dashboard')
    return "Invalid use maths/1234 <a href='/'>Back</a>"

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'teacher' not in session: return redirect('/')
    return render_template('teacher_dashboard.html', teacher=session['teacher'])

@app.route('/student_dashboard')
def student_dashboard():
    if 's_name' not in session: return redirect('/')
    my=[a for a in attendance if a['roll']==session['s_roll']]
    return render_template('student_dashboard.html', name=session['s_name'], roll=session['s_roll'], s_class=session['s_class'], my_att=my)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    sub=request.form.get('subject','maths'); sclass=request.form.get('class','TYCS')
    try: tlat=float(request.form.get('lat',0) or 0); tlng=float(request.form.get('lng',0) or 0)
    except: tlat=0; tlng=0
    token=str(random.randint(100000,999999)); exp=time.time()+60
    qr_store[token]={"class":sclass,"subject":sub,"exp":exp,"teacher":session.get('teacher',''),"lat":tlat,"lng":tlng}
    qr=qrcode.make(f"{token}|{sclass}|{sub}")
    buf=io.BytesIO(); qr.save(buf, format='PNG')
    img=base64.b64encode(buf.getvalue()).decode()
    return jsonify({"token":token,"class":sclass,"subject":sub,"img":img})

@app.route('/get_students')
def get_students(): return jsonify(students_db)
@app.route('/get_attendance')
def get_att(): return jsonify(attendance)

@app.route('/add_student', methods=['POST'])
def add_student():
    d=request.get_json()
    students_db.append({"name":d['name'],"roll":d['roll'],"class":d['class'],"email":d.get('email',''),"type":"Manual"})
    save(); return jsonify({"ok":True})

@app.route('/delete_student/<id>')
def del_stud(id):
    global students_db
    students_db=[s for s in students_db if s.get('email')!=id and s.get('roll')!=id]
    save(); return jsonify({"ok":True})

@app.route('/mark_attendance', methods=['POST'])
def mark_att():
    if 's_name' not in session: return jsonify({"msg":"❌ Login first"}),401
    d=request.get_json(); token=d.get('token','').split('|')[0].strip()
    try: slat=float(d.get('lat',0) or 0); slng=float(d.get('lng',0) or 0)
    except: slat=0; slng=0
    info=qr_store.get(token)
    if not info: return jsonify({"msg":"❌ Invalid QR"})
    if time.time()>info['exp']:
        if token in qr_store: del qr_store[token]
        return jsonify({"msg":"❌ QR Expired"})
    dist=0
    if info.get('lat',0)!=0 and slat!=0:
        dist_km=distance_km(info['lat'],info['lng'],slat,slng); dist=int(dist_km*1000)
        if dist_km>0.5: return jsonify({"msg":f"❌ Too far {dist}m - Come within 500m"})
    for a in attendance:
        if a['roll']==session['s_roll'] and a['token']==token: return jsonify({"msg":"⚠️ Already marked"})
    rec={"name":session['s_name'],"roll":session['s_roll'],"class":info['class'],"subject":info['subject'],"teacher":info['teacher'],"date":datetime.now().strftime("%d/%m/%Y %H:%M"),"token":token,"dist":dist}
    attendance.append(rec); save()
    return jsonify({"msg":f"✅ Present {info['subject']} {dist}m"})

@app.route('/download_attendance')
def down_att():
    si=io.StringIO(); w=csv.writer(si); w.writerow(["Date","Name","Roll","Class","Subject","Teacher","Distance"])
    for a in attendance: w.writerow([a.get('date',''),a.get('name',''),a.get('roll',''),a.get('class',''),a.get('subject',''),a.get('teacher',''),f"{a.get('dist',0)}m"])
    bi=io.BytesIO(); bi.write(si.getvalue().encode()); bi.seek(0)
    return send_file(bi, as_attachment=True, download_name="attendance.csv", mimetype="text/csv")

@app.route('/download_students')
def down_stu():
    si=io.StringIO(); w=csv.writer(si); w.writerow(["Name","Roll","Class","Email","Type"])
    for s in students_db: w.writerow([s.get('name',''),s.get('roll',''),s.get('class',''),s.get('email',''),s.get('type','')])
    bi=io.BytesIO(); bi.write(si.getvalue().encode()); bi.seek(0)
    return send_file(bi, as_attachment=True, download_name="students.csv", mimetype="text/csv")

@app.route('/logout')
def logout(): session.clear(); return redirect('/')
if __name__=='__main__': app.run(debug=True)
