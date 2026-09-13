from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from authlib.integrations.flask_client import OAuth
import sqlite3
import segno
import os
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)
app.secret_key = "attendance123"

DATABASE = "database/database.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

def create_tables():

    conn = get_db()
    cursor = conn.cursor()

    # ---------------- STUDENTS ---------------- #

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            roll TEXT UNIQUE NOT NULL,

            class TEXT NOT NULL,

            email TEXT,

            phone TEXT,

            username TEXT UNIQUE,

            password TEXT
        )
    """)

    # ---------------- ATTENDANCE ---------------- #

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student TEXT NOT NULL,

            subject TEXT NOT NULL,

            class_name TEXT,

            division TEXT,

            date TEXT,

            time TEXT,

            status TEXT
        )
    """)

    # ---------------- QR CODES ---------------- #

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            qr_token TEXT UNIQUE NOT NULL,

            subject TEXT NOT NULL,

            class_name TEXT,

            division TEXT,

            created_at TEXT,

            expires_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# HOME / LOGIN PAGE
# ============================================================

@app.route("/")
def home():

    # If already logged in, send user to dashboard

    if "user" in session:

        if session.get("role") == "teacher":
            return redirect(url_for("teacher_dashboard"))

        if session.get("role") == "student":
            return redirect(url_for("student_dashboard"))

    return render_template("login.html")

# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    # ==========================================
    # TEACHER LOGIN
    # ==========================================

    if role == "teacher":

        # Your existing teacher username/password
        if username == "teacher" and password == "1234":

            session["user"] = username
            session["name"] = "Teacher"
            session["role"] = "teacher"

            return redirect(url_for("teacher_dashboard"))

        return "Invalid teacher username or password"

    # ==========================================
    # STUDENT LOGIN
    # ==========================================

    if role == "student":

        conn = get_db()
        student = conn.execute(
            "SELECT * FROM students WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if student and check_password_hash(student["password"], password):

            session["user"] = username
            session["name"] = student["name"]
            session["role"] = "student"

            return redirect(url_for("student_dashboard"))

        return "Invalid student username or password"

    return "Please select a valid return"
    


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@app.route("/teacher_dashboard")
def teacher_dashboard():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    return render_template(
        "teacher_dashboard.html"
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student_dashboard")
def student_dashboard():

    if session.get("role") != "student":

        return redirect(url_for("home"))

    return render_template(
        "student_dashboard.html"
    )


# ============================================================
# ADD STUDENT PAGE
# ============================================================

@app.route("/add_student")
def add_student():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    return render_template(
        "add_student.html"
    )


# ============================================================
# SAVE STUDENT
# ============================================================

@app.route("/save_student", methods=["POST"])
def save_student():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    name = request.form.get("name", "").strip()
    roll = request.form.get("roll", "").strip()
    class_name = request.form.get("class", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()

    # Validate

    if not name or not roll or not class_name or not password:

        return """
        <h2>Please fill all required fields.</h2>
        <a href="/add_student">Back</a>
        """

    # Username = Roll Number

    username = roll

    # Hash password

    password_hash = generate_password_hash(
        password
    )

    conn = get_db()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO students
            (
                name,
                roll,
                class,
                email,
                phone,
                username,
                password
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            roll,
            class_name,
            email,
            phone,
            username,
            password,

        ))

        conn.commit()

    except sqlite3.IntegrityError:

        conn.close()

        return """
        <h2>Roll Number or Username already exists!</h2>
        <a href="/add_student">Back to Add Student</a>
        """

    conn.close()

    return redirect(
        url_for("student_list")
    )


# ============================================================
# STUDENT LIST
# ============================================================

@app.route("/student_list")
def student_list():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            roll,
            class,
            email,
            phone,
            username
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "student_list.html",
        students=students
    )


# ============================================================
# DELETE STUDENT
# ============================================================

@app.route("/delete_student/<int:student_id>")
def delete_student(student_id):

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("student_list")
    )


# ============================================================
# CREATE LECTURE PAGE
# ============================================================

@app.route("/create_lecture")
def create_lecture():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    return render_template(
        "create_lecture.html"
    )


# ============================================================
# GENERATE QR CODE
# ============================================================

@app.route("/generate_qr", methods=["POST"])
def generate_qr():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    class_name = request.form.get(
        "class",
        ""
    ).strip()

    division = request.form.get(
        "division",
        ""
    ).strip()

    if not subject:

        return """
        <h2>Subject is required.</h2>
        <a href="/create_lecture">Back</a>
        """

    # --------------------------------------------------------
    # Generate unique QR token
    # --------------------------------------------------------

    token = str(uuid.uuid4())

    created_at = datetime.now()

    # QR valid for 2 minutes

    expires_at = created_at + timedelta(
        minutes=2
    )

    # --------------------------------------------------------
    # Save QR information in database
    # --------------------------------------------------------

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO qr_codes
        (
            qr_token,
            subject,
            class_name,
            division,
            created_at,
            expires_at
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        token,
        subject,
        class_name,
        division,
        created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        expires_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    conn.commit()
    conn.close()

    # --------------------------------------------------------
    # QR data
    # --------------------------------------------------------

    qr_data = f"ATTENDANCE:{token}"

    qr = segno.make(
        qr_data
    )

    # --------------------------------------------------------
    # QR folder
    # --------------------------------------------------------

    qr_folder = os.path.join(
        "static",
        "qr_codes"
    )

    os.makedirs(
        qr_folder,
        exist_ok=True
    )

    filename = "attendance_qr.png"

    filepath = os.path.join(
        qr_folder,
        filename
    )

    qr.save(
        filepath,
        scale=8
    )

    # --------------------------------------------------------
    # Display QR
    # --------------------------------------------------------

    return render_template(
        "generate_qr.html",

        subject=subject,

        class_name=class_name,

        division=division,

        qr_image=filename,

        expires_at=expires_at.strftime(
            "%H:%M:%S"
        )
    )


# ============================================================
# SCAN QR PAGE
# ============================================================

@app.route("/scan_qr")
def scan_qr():

    if session.get("role") != "student":

        return redirect(url_for("home"))

    return render_template(
        "scan_qr.html"
    )


# ============================================================
# MARK ATTENDANCE
# ============================================================

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():

    # --------------------------------------------------------
    # Student must be logged in
    # --------------------------------------------------------

    if session.get("role") != "student":

        return jsonify({
            "success": False,
            "message": "Please login as a student first."
        }), 401


    # --------------------------------------------------------
    # Get QR data
    # --------------------------------------------------------

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "No QR data received."
        }), 400


    qr_data = data.get(
        "qr_data",
        ""
    ).strip()


    if not qr_data:

        return jsonify({
            "success": False,
            "message": "Invalid QR code."
        }), 400


    # --------------------------------------------------------
    # Check QR format
    # --------------------------------------------------------

    if not qr_data.startswith(
        "ATTENDANCE:"
    ):

        return jsonify({
            "success": False,
            "message": "This is not a valid attendance QR."
        }), 400


    token = qr_data.replace(
        "ATTENDANCE:",
        "",
        1
    ).strip()


    # --------------------------------------------------------
    # Find QR in database
    # --------------------------------------------------------

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM qr_codes
        WHERE qr_token = ?
    """, (token,))

    qr = cursor.fetchone()


    if not qr:

        conn.close()

        return jsonify({
            "success": False,
            "message": "QR code not found."
        }), 404


    # --------------------------------------------------------
    # Check QR expiry
    # --------------------------------------------------------

    expires_at = datetime.strptime(
        qr["expires_at"],
        "%Y-%m-%d %H:%M:%S"
    )

    if datetime.now() > expires_at:

        conn.close()

        return jsonify({
            "success": False,
            "message": "QR code has expired."
        })


    # --------------------------------------------------------
    # Get logged-in student
    # --------------------------------------------------------

    student_name = session.get(
        "user"
    )

    student_roll = session.get(
        "roll"
    )


    # --------------------------------------------------------
    # Prevent duplicate attendance
    # --------------------------------------------------------

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cursor.execute("""
        SELECT id
        FROM attendance

        WHERE student = ?
        AND subject = ?
        AND date = ?
    """, (
        student_roll,
        qr["subject"],
        today
    ))

    already_marked = cursor.fetchone()


    if already_marked:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Attendance already marked for this lecture."
        })


    # --------------------------------------------------------
    # Insert attendance
    # --------------------------------------------------------

    cursor.execute("""
        INSERT INTO attendance
        (
            student,
            subject,
            class_name,
            division,
            date,
            time,
            status
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        student_roll,
        qr["subject"],
        qr["class_name"],
        qr["division"],
        today,
        datetime.now().strftime(
            "%H:%M:%S"
        ),
        "Present"
    ))

    conn.commit()
    conn.close()


    return jsonify({
        "success": True,
        "message":
            f"Attendance marked successfully for {student_name}!"
    })


# ============================================================
# ATTENDANCE REPORT
# ============================================================

@app.route("/attendance_report")
def attendance_report():

    if session.get("role") != "teacher":

        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM attendance
        ORDER BY date DESC, time DESC
    """)

    attendance = cursor.fetchall()

    conn.close()

    return render_template(
        "attendance_report.html",
        attendance=attendance
    )


# ============================================================
# STUDENT ATTENDANCE
# ============================================================

@app.route("/my_attendance")
def my_attendance():

    if session.get("role") != "student":

        return redirect(url_for("home"))

    roll = session.get(
        "roll"
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM attendance
        WHERE student = ?
        ORDER BY date DESC, time DESC
    """, (roll,))

    attendance = cursor.fetchall()

    conn.close()

    return render_template(
        "my_attendance.html",
        attendance=attendance
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ---------------- GOOGLE LOGIN ---------------- #

@app.route("/google/login")
def google_login():
    redirect_uri = url_for(
    "google_callback",
    _external=True,
    _scheme="http"
    )   
    return google.authorize_redirect(redirect_uri)


@app.route("/google/callback")
def google_callback():

    token = google.authorize_access_token()

    user_info = token.get("userinfo")

    if not user_info:
        return "Could not get Google account information."

    email = user_info["email"]
    name = user_info.get("name", "")

    session["user"] = name
    session["email"] = email
    session["role"] = "student"

    return redirect(url_for("student_dashboard"))




# ============================================================
# ERROR HANDLER
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return """
    <h1>404 - Page Not Found</h1>
    <a href="/">Go to Login</a>
    """, 404


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

    # Create database and tables

    create_tables()

    print("")
    print("======================================")
    print("     QR ATTENDANCE SYSTEM")
    print("======================================")
    print("")
    print("Teacher Login:")
    print("Username: teacher")
    print("Password: 1234")
    print("")
    print("Website:")
    print("http://127.0.0.1:5000")
    print("")
    print("======================================")
    print("")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
