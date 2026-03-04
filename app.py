from flask import Flask, render_template, request, redirect, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from questions import questions
import time
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

EXAM_DURATION = 45 * 60  # 45 minutes

# ---------------- GOOGLE SHEET SETUP ---------------- #

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Exam Results").sheet1


# ---------------- REGISTER PAGE ---------------- #

@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        dept = request.form["dept"]

        # Prevent duplicate roll number
        records = sheet.get_all_records()

        for row in records:
            if str(row.get("Roll", "")).strip() == roll.strip():
                return "You already attended the exam!"

        # Store session data
        session["name"] = name
        session["roll"] = roll
        session["dept"] = dept
        session["start_time"] = int(time.time())
        session["submitted"] = False

        return redirect("/exam")

    return render_template("register.html")


# ---------------- EXAM PAGE ---------------- #

@app.route("/exam", methods=["GET", "POST"])
def exam():
    if "name" not in session:
        return redirect("/")

    start_time = session.get("start_time")
    current_time = int(time.time())
    time_left = EXAM_DURATION - (current_time - start_time)

    if time_left <= 0:
        return redirect("/submit")

    if request.method == "POST":
        score = 0
        for q in questions:
            selected = request.form.get(str(q["id"]))
            if selected == q["answer"]:
                score += 1

        session["score"] = score
        return redirect("/submit")

    return render_template(
        "exam.html",
        questions=questions,
        time_left=time_left
    )


# ---------------- SUBMIT PAGE ---------------- #

@app.route("/submit")
def submit():
    if "name" not in session:
        return redirect("/")

    # Prevent duplicate submission
    if session.get("submitted"):
        return "Already submitted!"

    name = session.get("name")
    roll = session.get("roll")
    dept = session.get("dept")
    score = session.get("score", 0)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save to Google Sheet
    sheet.append_row([name, roll, dept, score, now])

    session["submitted"] = True
    session.clear()

    return render_template("result.html", score=score)


if __name__ == "__main__":
    app.run(debug=True)
