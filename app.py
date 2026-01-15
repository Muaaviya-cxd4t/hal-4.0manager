from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("main.html")

@app.route("/judge")
def judge_login():
    return render_template("loginj.html")

@app.route("/coordinator")
def coordinator_login():
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
