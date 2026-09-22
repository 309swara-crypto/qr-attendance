<body style="font-family:Arial; padding:20px;">
<h2>Complete Registration</h2>
<p>Hi {{name}} ({{email}})</p>
<form action="/register_student" method="POST">
<input name="roll" placeholder="Enter Roll No" required style="padding:10px; width:90%;"><br><br>
<input name="class_name" placeholder="Enter Class e.g. TYCS" required style="padding:10px; width:90%;"><br><br>
<button type="submit" style="padding:12px; background:green; color:white; width:95%;">Save & Continue</button>
</form>
</body>
