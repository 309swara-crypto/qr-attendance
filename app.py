from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>QR Attendance LIVE ✅</h1><p>Base working. Next add 6 buttons + QR</p>"

@app.route('/login')
def login():
    return "Login page - teacher: dbms/stqa/cis pass 1234"

if __name__ == "__main__":
    app.run()
