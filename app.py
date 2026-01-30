import sqlite3
import pandas as pd
import os
from flask import Flask, request, render_template, redirect, url_for
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "main"

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect("qrcodes.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id TEXT PRIMARY KEY,
            breakfast INTEGER DEFAULT 0,
            lunch INTEGER DEFAULT 0,
            dinner INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# ---------------- USERS ----------------

class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def verify(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

users = {
    "foodadmin": User("1", "foodadmin",
        bcrypt.generate_password_hash("food123").decode(), "food"),
    "judge": User("2", "judge",
        bcrypt.generate_password_hash("judge123").decode(), "logistics"),
}

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if user.id == user_id:
            return user
    return None

# ---------------- ROUTES ----------------

@app.route("/")
def main():
    return render_template("main.html")

# ---- FOOD LOGIN ----
@app.route("/login-food", methods=["GET", "POST"])
def login_food():
    if request.method == "POST":
        u = users.get(request.form["username"])
        if u and u.role == "food" and u.verify(request.form["password"]):
            login_user(u)
            return redirect(url_for("scanner"))
    return render_template("login.html")

# ---- LOGISTICS LOGIN ----
@app.route("/login-logistics", methods=["GET", "POST"])
def login_logistics():
    if request.method == "POST":
        u = users.get(request.form["username"])
        if u and u.role == "logistics" and u.verify(request.form["password"]):
            login_user(u)
            return redirect(url_for("judges"))
    return render_template("loginL.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main"))

# ---------------- PAGES ----------------

@app.route("/scanner")
@login_required
def scanner():
    if current_user.role != "food":
        return redirect(url_for("main"))
    return render_template("scanner.html")

@app.route("/judges")
@login_required
def judges():
    if current_user.role != "logistics":
        return redirect(url_for("main"))

    CSV_PATH = os.path.join(os.path.dirname(__file__), "teams.csv")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")


    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns={df.columns[0]: "team"}, inplace=True)

    teams = df["team"].tolist()

    return render_template("judges.html", teams=teams)


@app.route("/submit-judging", methods=["POST"])
@login_required
def submit_judging():
    if current_user.role != "logistics":
        return redirect(url_for("main"))

    team = request.form["team"].strip()

    CSV_PATH = os.path.join(os.path.dirname(__file__), "teams.csv")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # 🔥 FORCE FIX COLUMN NAMES
    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns={df.columns[0]: "team"}, inplace=True)

    df.loc[df["team"].str.strip() == team, [
        "creativity",
        "innovation",
        "code_quality",
        "problem_solving"
    ]] = [
        int(request.form["creativity"]),
        int(request.form["innovation"]),
        int(request.form["code_quality"]),
        int(request.form["problem_solving"])
    ]

    df.to_csv(CSV_PATH, index=False)

    return redirect(url_for("judges"))


# ---------------- QR LOGIC (unchanged, just cleaned) ----------------

def get_current_meal():
    now = datetime.now().time()
    if datetime.strptime("06:00", "%H:%M").time() <= now < datetime.strptime("10:00", "%H:%M").time():
        return "breakfast"
    if datetime.strptime("12:00", "%H:%M").time() <= now < datetime.strptime("15:00", "%H:%M").time():
        return "lunch"
    if datetime.strptime("18:00", "%H:%M").time() <= now < datetime.strptime("21:00", "%H:%M").time():
        return "dinner"
    return None

@app.route("/scan_qr", methods=["POST"])
@login_required
def scan_qr():
    if current_user.role != "food":
        return "Unauthorized", 403

    pid = request.form["id"]
    meal = get_current_meal()
    if not meal:
        return "Not meal time", 400

    conn = sqlite3.connect("qrcodes.db")
    c = conn.cursor()

    c.execute(f"SELECT {meal} FROM participants WHERE id=?", (pid,))
    row = c.fetchone()

    if not row:
        conn.close()
        return "Invalid QR", 400

    if row[0] == 1:
        conn.close()
        return "Already used", 400

    c.execute(f"UPDATE participants SET {meal}=1 WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return "Food can be served", 200

# ---------------- RUN ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
