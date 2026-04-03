from flask import Flask, render_template, request, redirect, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from questions import questions
import time
import os
import random
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
        name = request.form["name"].strip()
        roll = request.form["roll"].strip()
        dept = request.form["dept"].strip()

        # ✅ Fast duplicate check
        try:
            roll_list = [r.strip() for r in sheet.col_values(2)]
        except:
            roll_list = []

        if roll in roll_list:
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

    # Auto submit if time over
    if time_left <= 0:
        return redirect("/submit")

    # 🔀 Shuffle only once per student
    if "shuffled_questions" not in session:
        shuffled = questions.copy()
        random.shuffle(shuffled)

        # Shuffle options also
        for q in shuffled:
            random.shuffle(q["options"])

        session["shuffled_questions"] = shuffled

    # 🧮 Calculate score
    if request.method == "POST":
        score = 0

        for q in session["shuffled_questions"]:
            selected = request.form.get(str(q["id"]))
            if selected == q["answer"]:
                score += 1

        session["score"] = score
        return redirect("/submit")

    # Render exam
    return render_template(
        "exam.html",
        questions=session["shuffled_questions"],
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

    # ✅ Safe Google Sheet write
    try:
        time.sleep(0.5)  # small delay (better than 1 sec)
        sheet.append_row([name, roll, dept, score, now])
    except Exception as e:
        print("Sheet write failed:", e)

    session["submitted"] = True
    session.clear()

    return render_template("result.html", score=score)


# ---------------- RUN APP ---------------- #

if __name__ == "__main__":
    app.run(debug=True)
