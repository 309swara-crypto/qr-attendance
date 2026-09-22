from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import qrcode, io, base64, time, random, csv, math
from datetime import datetime
app = Flask(__name__)
app.secret_key = "vcet_google_real_final_2026"
TEACHERS = {"dbms":"1234","admin":"admin","teacher":"teacher"}
CLASSES = ["TE-A","TE-B","TE-C","TYCS","SYCS","FYCS"]
SUBJECTS = ["DBMS","OS","CN","AI","ML","SE","IP","IOT"]
qr_store = {}; attendance = []; students_db = []
def distance_km(lat1,lon1,lat2,lon2):
    if not lat1 or not lon1 or not lat2 or not lon2: return 0
    R=6371; dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.asin(math.sqrt(a))
@app.route('/')
def home(): return render_template('home.html')
@app.route('/teacher_login_page')
def teacher_login_page(): return render_template('teacher_dashboard.html', is_login=True)
@app.route('/student_login_page')
def student_login_page(): return render_template('student_dashboard.html', is_login=True)
@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    uid=request.form.get('uid','').lower(); pwd=request.form.get('pwd','')
    if TEACHERS.get(uid)==pwd: session['teacher']=uid; return redirect('/teacher_dashboard')
    return "Invalid Use dbms/1234"
@app.route('/google_login', methods=['POST'])
def google_login():
    d=request.get_json(); role=d.get('role'); email=d.get('email',''); name=d.get('name', email.split('@')[0])
    if role=='teacher':
        session['teacher']=email.split('@')[0]; session['t_email']=email; session['t_name']=name
        return jsonify({"redirect":"/teacher_dashboard"})
    else:
        existing = next((s for s in students_db if s.get('email','').lower()==email.lower()), None)
        if existing:
            session['s_name']=existing['name']; session['s_roll']=existing['roll']; session['s_class']=existing['class']; session['s_email']=email
            return jsonify({"redirect":"/student_dashboard"})
        else: return jsonify({"need_details":True, "email":email, "name":name})
@app.route('/google_complete_register', methods=['POST'])
def google_complete_register():
    d=request.get_json(); session['s_name']=d['name']; session['s_roll']=d['roll']; session['s_class']=d['class']; session['s_email']=d['email']
    if not any(s.get('email','').lower()==d['email'].lower() for s in students_db):
        students_db.append({"name":d['name'],"roll":d['roll'],"class":d['class'],"email":d['email'],"via":"Google"})
    return jsonify({"redirect":"/student_dashboard"})
@app.route('/student_register', methods=['POST'])
def student_register():
    d=request.get_json(); session['s_name']=d['name']; session['s_roll']=d['roll']; session['s_class']=d['class']
    if not any(s['roll']==d['roll'] for s in students_db): students_db.append({"name":d['name'],"roll":d['roll'],"class":d['class'],"email":d.get('email',''),"via":"Manual"})
    return jsonify({"ok":True})
@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'teacher' not in session: return redirect('/teacher_login_page')
    return render_template('teacher_dashboard.html', is_login=False, teacher=session['teacher'], classes=CLASSES, subjects=SUBJECTS, sc=len(students_db), ac=len(attendance))
@app.route('/student_dashboard')
def student_dashboard():
    if 's_name' not in session: return redirect('/student_login_page')
    my_att=[a for a in attendance if a['roll']==session['s_roll']]
    return render_template('student_dashboard.html', is_login=False, name=session['s_name'], roll=session['s_roll'], my_att=my_att)
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    if 'teacher' not in session: return jsonify({"error":"login"}),401
    cls=request.form.get('class'); sub=request.form.get('subject')
    try: t_lat=float(request.form.get('lat',0) or 0); t_lng=float(request.form.get('lng',0) or 0)
    except: t_lat=0; t_lng=0
    token=str(random.randint(100000,999999)); exp=time.time()+120
    qr_store[token]={"class":cls,"subject":sub,"exp":exp,"teacher":session['teacher'],"lat":t_lat,"lng":t_lng}
    qr_text=f"{token}|{cls}|{sub}|{int(exp)}"; qr=qrcode.make(qr_text); buf=io.BytesIO(); qr.save(buf, format='PNG')
    img=base64.b64encode(buf.getvalue()).decode()
    return jsonify({"token":token,"class":cls,"subject":sub,"img":img})
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 's_name' not in session: return jsonify({"msg":"❌ Login first"}),401
    d=request.get_json(); token=d.get('token','').strip().split('|')[0]
    try: s_lat=float(d.get('lat',0) or 0); s_lng=float(d.get('lng',0) or 0)
    except: s_lat=0; s_lng=0
    info=qr_store.get(token)
    if not info: return jsonify({"msg":"❌ Invalid QR"})
    if time.time()>info['exp']: del qr_store[token]; return jsonify({"msg":"❌ QR Expired"})
    dist=0
    if info['lat']!=0 and s_lat!=0:
        dist_km=distance_km(info['lat'],info['lng'],s_lat,s_lng); dist=int(dist_km*1000)
        if dist_km>0.5: return jsonify({"msg":f"❌ Too far {dist}m"})
    for a in attendance:
        if a['roll']==session['s_roll'] and a['token']==token: return jsonify({"msg":"⚠️ Already marked"})
    rec={"name":session['s_name'],"roll":session['s_roll'],"class":info['class'],"subject":info['subject'],"teacher":info['teacher'],"time":datetime.now().strftime("%d-%m-%Y %H:%M:%S"),"token":token,"dist":dist}
    attendance.append(rec); return jsonify({"msg":f"✅ Present {info['subject']} {dist}m"})
@app.route('/get_attendance')
def get_attendance(): return jsonify(attendance)
@app.route('/add_student', methods=['POST'])
def add_student(): students_db.append({"name":request.form.get('name'),"roll":request.form.get('roll'),"class":request.form.get('class'),"email":request.form.get('email'),"via":"Teacher"}); return jsonify({"ok":True})
@app.route('/download_attendance')
def download_attendance():
    if not attendance: return "No data"
    si=io.StringIO(); w=csv.writer(si); w.writerow(["Name","Roll","Class","Subject","Teacher","Time","Dist"]); [w.writerow([a['name'],a['roll'],a['class'],a['subject'],a['teacher'],a['time'],a.get('dist',0)]) for a in attendance]
    bi=io.BytesIO(); bi.write(si.getvalue().encode()); bi.seek(0); return send_file(bi, as_attachment=True, download_name="attendance.csv", mimetype="text/csv")
@app.route('/logout')
def logout(): session.clear(); return redirect('/')
if __name__=='__main__': app.run(debug=True)
