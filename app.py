from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import qrcode, io, base64, time, random, csv
from datetime import datetime
app = Flask(__name__)
app.secret_key = "video_same_2026"
TEACHERS={"dbms":"1234","stqa":"1234","cis":"1234","maths":"1234"}
CLASSES=["TE-A","TE-B","TE-C","TYCS","SYCS","TYBSC-CS"]
SUBJECTS=["DBMS","STQA","CIS","MATHS","JAVA","PYTHON"]
qr_store={}; attendance=[]; students_db=[]
@app.route('/')
def home(): return render_template('home.html')
@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    u=request.form['uid']; p=request.form['pwd']
    if TEACHERS.get(u)==p:
        session['teacher']=u; return redirect('/teacher_dashboard')
    return "Wrong! dbms/1234 <a href=/>Back</a>"
@app.route('/google_login', methods=['POST'])
def google_login():
    d=request.get_json(); role=d.get('role'); email=d.get('email','')
    if role=='teacher':
        session['teacher']=email.split('@')[0]; session['teacher_email']=email
        return jsonify({"redirect":"/teacher_dashboard"})
    else:
        session['s_name']=email.split('@')[0]; session['s_roll']=email.split('@')[0]
        session['s_email']=email; return jsonify({"redirect":"/student_dashboard"})
@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'teacher' not in session: return redirect('/')
    return render_template('tr_dashboard.html', teacher=session['teacher'], classes=CLASSES, subjects=SUBJECTS, sc=len(students_db), ac=len(attendance))
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    c=request.form['class']; s=request.form['subject']
    token=str(int(time.time()))[-6:]+str(random.randint(10,99))
    qr_store[token]={"class":c,"subject":s,"time":time.time(),"teacher":session['teacher']}
    qr=qrcode.make(f"{token}|{c}|{s}"); buf=io.BytesIO(); qr.save(buf, format='PNG')
    img=base64.b64encode(buf.getvalue()).decode()
    return jsonify({"token":token,"img":img,"class":c,"subject":s})
@app.route('/get_students')
def get_students(): return jsonify(students_db)
@app.route('/add_student', methods=['POST'])
def add_student():
    students_db.append({"name":request.form['name'],"roll":request.form['roll'],"class":request.form['class'],"email":request.form.get('email',''),"year":"TY"})
    return jsonify({"ok":1})
@app.route('/get_attendance')
def get_attendance(): return jsonify(attendance)
@app.route('/download_attendance')
def download_attendance():
    out=io.StringIO(); w=csv.writer(out); w.writerow(['Name','Roll','Class','Subject','Time','Teacher'])
    for a in attendance: w.writerow([a['name'],a['roll'],a['class'],a.get('subject',''),a['time'],a.get('teacher','')])
    mem=io.BytesIO(); mem.write(out.getvalue().encode()); mem.seek(0)
    return send_file(mem, download_name="attendance.csv", as_attachment=True)
@app.route('/students_excel')
def students_excel():
    out=io.StringIO(); w=csv.writer(out); w.writerow(['Name','Roll','Class','Email'])
    for s in students_db: w.writerow([s['name'],s['roll'],s['class'],s['email']])
    mem=io.BytesIO(); mem.write(out.getvalue().encode()); mem.seek(0)
    return send_file(mem, download_name="students.csv", as_attachment=True)
@app.route('/student_register', methods=['POST'])
def student_register():
    d=request.get_json(); session['s_name']=d['name']; session['s_roll']=d['roll']; session['s_class']=d.get('class','TE-A'); session['s_email']=d.get('email','')
    students_db.append({"name":d['name'],"roll":d['roll'],"class":d.get('class','TE-A'),"email":d.get('email',''),"year":"TY"})
    return jsonify({"ok":1})
@app.route('/student_dashboard')
def student_dashboard():
    if 's_roll' not in session: return redirect('/')
    my=[a for a in attendance if a['roll']==session['s_roll']]
    return render_template('studnet_dashboard.html', name=session['s_name'], roll=session['s_roll'], my_att=my)
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    d=request.get_json(); token=d['token'].split('|')[0].strip(); qr=qr_store.get(token)
    if not qr: return jsonify({"msg":"❌ Invalid QR"})
    if time.time()-qr['time']>35: return jsonify({"msg":"❌ Expired"})
    attendance.append({"name":session.get('s_name',''),"roll":session.get('s_roll',''),"class":qr['class'],"subject":qr['subject'],"time":datetime.now().strftime("%d-%m-%Y %H:%M:%S"),"teacher":qr['teacher'],"email":session.get('s_email','')})
    return jsonify({"msg":f"✅ Marked {qr['subject']}-{qr['class']}"})
@app.route('/logout')
def logout(): session.clear(); return redirect('/')
if __name__=="__main__": app.run()
