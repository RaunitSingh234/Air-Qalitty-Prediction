from dotenv import load_dotenv
import os
load_dotenv()

from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import mysql.connector
import numpy as np
from sklearn.linear_model import LinearRegression
import csv
from flask import make_response


app = Flask(__name__, template_folder="templates")
app.secret_key = "airaware_secret"

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

# -------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()

        if user:
            session["user"] = user["username"]
            return redirect("/dashboard")
        else:
            return "Invalid Login"

    return render_template("login.html")


# -------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT city,
        AVG(pm25) AS pm25,
        AVG(pm10) AS pm10
        FROM air_quality
        GROUP BY city
    """)
    data = cur.fetchall()

    return render_template("dashboard.html", data=data)

# -------- ABOUT PAGE ----------
@app.route("/about")
def about():
    return render_template("about.html")



# -------- MONTHLY DATA API FOR JS --------
@app.route("/monthly-data")
def monthly_data():
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT MONTH(from_date) AS month, AVG(pm25) AS pm25, AVG(pm10) AS pm10
        FROM air_quality
        GROUP BY MONTH(from_date)
        ORDER BY month
    """)
    return jsonify(cur.fetchall())

# -------- PREDICTION PAGE ----------
@app.route("/prediction", methods=["GET", "POST"])
def prediction():
    result = None

    if request.method == "POST":
        pm25 = float(request.form.get("pm25", 0) or 0)
        pm10 = float(request.form.get("pm10", 0) or 0)

# AQI (simple combined index)
        aqi = (pm25 * 0.6) + (pm10 * 0.4)

# Indian AQI Category
        if aqi <= 50:
            status = "Good"
        elif aqi <= 100:
            status = "Satisfactory"
        elif aqi <= 200:
            status = "Moderate"
        elif aqi <= 300:
            status = "Poor"
        elif aqi <= 400:
            status = "Very Poor"
        else:
            status = "Severe"


        result = (round(aqi, 2), status)

    return render_template("prediction.html", result=result)


# -------- HEALTH ADVISOR ----------
@app.route("/health", methods=["GET", "POST"])
def health():
    result = None

    if request.method == "POST":
        aqi = int(request.form["aqi"])

        if aqi <= 50:
            level = "Good"
            color = "green"
            advice = "Air quality is good. Enjoy normal outdoor activities."
            mask = "No mask needed "
            risk = "No risk for anyone."
        elif aqi <= 100:
            level = "Satisfactory"
            color = "lightgreen"
            advice = "Air quality is acceptable. Slight risk to sensitive people."
            mask = "Mask optional."
            risk = "Children, elderly & asthma patients be cautious."
        elif aqi <= 200:
            level = "Moderate"
            color = "yellow"
            advice = "Reduce prolonged outdoor exertion."
            mask = "Wear mask if you have breathing problems."
            risk = "Asthma, lung & heart patients at risk."
        elif aqi <= 300:
            level = "Poor"
            color = "orange"
            advice = "Avoid heavy outdoor exercise."
            mask = "N95 mask recommended 😷"
            risk = "Children & elderly should stay indoors."
        elif aqi <= 400:
            level = "Very Poor"
            color = "red"
            advice = "Stay indoors. Avoid outdoor activity."
            mask = "N95/N99 mask required."
            risk = "High risk for everyone."
        else:
            level = "Severe"
            color = "purple"
            advice = "Health emergency! Avoid going out completely."
            mask = "N99 mask strictly required "
            risk = "Serious risk. Can impact even healthy people."

        result = {
            "aqi": aqi,
            "level": level,
            "color": color,
            "advice": advice,
            "mask": mask,
            "risk": risk
        }

    return render_template("health.html", result=result)


#-------------feedback-----------------

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    msg = None

    if request.method == "POST":
        name = request.form["name"]
        fb = request.form["message"]

        cur = db.cursor()
        cur.execute("INSERT INTO feedback(name, message) VALUES(%s,%s)", (name, fb))
        db.commit()

        msg = "Feedback submitted successfully "

    return render_template("feedback.html", msg=msg)

#------------ CHATBOT -------------


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if "chat" not in session:
        session["chat"] = []   # store full conversation

    if request.method == "POST":
        user_msg = request.form["question"]
        session["chat"].append(("user", user_msg))

        q = user_msg.lower()

        # --- SMART REPLY ENGINE ---
        if "hello" in q or "hi" in q:
            bot = "Hello .. How can I help you about air quality?"
        elif "aqi" in q:
            bot = "AQI stands for Air Quality Index. Higher AQI = more pollution."
        elif "pm2.5" in q:
            bot = "PM2.5 are tiny particles smaller than 2.5 microns that can enter lungs and bloodstream."
        elif "pm10" in q:
            bot = "PM10 are dust particles ≤10 microns that affect throat and nose."
        elif "mask" in q:
            bot = "Wear N95 mask when AQI is Poor or Very Poor 😷"
        elif "health" in q or "problem" in q:
            bot = "Poor AQI may trigger asthma, coughing, eye irritation and heart stress."
        elif "tips" in q or "advice" in q:
            bot = "Stay indoors, use N95 mask, keep plants, avoid morning walk in heavy traffic."
        elif "goodbye" in q or "bye" in q:
            bot = "Goodbye .. Stay safe and monitor AQI regularly."
        else:
            bot = "I'm a simple chatbot 🤖. Ask about AQI, PM2.5, mask, health, tips etc."

        session["chat"].append(("bot", bot))

    return render_template("chatbot.html", chat=session["chat"])


# -------- LANGUAGE SWITCHER ----------

translations = {
    "en": {
        "dashboard": "Dashboard",
        "about": "About",
        "prediction": "Prediction",
        "health": "Health Advisor",
        "feedback": "Feedback",
        "chatbot": "Chatbot",
        "download": "Download",
        "logout": "Logout",
        "total_cities": "Total Cities",
        "pm25_avg": "PM2.5 Avg",
        "pm10_avg": "PM10 Avg",
        "monthwise": "Month-wise Pollution Trend",
        "citywise": "City-wise Air Pollution",
    },

    "hi": {
        "dashboard": "डैशबोर्ड",
        "about": "परिचय",
        "prediction": "पूर्वानुमान",
        "health": "स्वास्थ्य सलाहकार",
        "feedback": "प्रतिक्रिया",
        "chatbot": "चैटबॉट",
        "download": "डाउनलोड",
        "logout": "लॉग आउट",
        "total_cities": "कुल शहर",
        "pm25_avg": "PM2.5 औसत",
        "pm10_avg": "PM10 औसत",
        "citywise": "शहरवार वायु प्रदूषण",
        "monthwise": "मासिक प्रदूषण प्रवृत्ति",
    }
}


@app.context_processor
def inject_language():
    lang = session.get("lang", "en")
    return dict(t=translations[lang])


@app.route("/lang/<code>")
def change_lang(code):
    session["lang"] = code
    return redirect(request.referrer or url_for("dashboard"))




# -------- DATA DOWNLOAD ----------

@app.route("/download")
def download_page():
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT DISTINCT city FROM air_quality")
    cities = cur.fetchall()
    return render_template("download.html", cities=cities)
# -------- FULL DATA DOWNLOAD ----------

@app.route("/download-data")
def download_data():
    cur = db.cursor()
    cur.execute("SELECT * FROM air_quality")
    rows = cur.fetchall()

    header = [d[0] for d in cur.description]
    data = [header] + list(rows)

    lines = []
    for r in data:
        lines.append(",".join([str(x) for x in r]))

    from flask import make_response
    response = make_response("\n".join(lines))
    response.headers["Content-Disposition"] = "attachment; filename=all_air_data.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# -------- CITY-WISE DATA DOWNLOAD ----------

@app.route("/download-by-city")
def download_by_city():
    city = request.args.get("city")

    cur = db.cursor()
    cur.execute("""
        SELECT * FROM air_quality WHERE city=%s
    """, (city,))
    rows = cur.fetchall()

    header = [d[0] for d in cur.description]
    data = [header] + list(rows)

    lines = []
    for r in data:
        lines.append(",".join([str(x) for x in r]))

    from flask import make_response
    response = make_response("\n".join(lines))
    response.headers["Content-Disposition"] = f"attachment; filename={city}_data.csv"
    response.headers["Content-Type"] = "text/csv"
    return response







# -------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
