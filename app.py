from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

# מילון משתמשים: ת"ז -> סיסמה
users = {
    "123456789": "pass123"
}

# היסטוריה לפי משתמש (רק בזיכרון, לא נשמר)
user_history_data = {}

def is_valid_id(user_id):
    return bool(re.match(r'^\d{9}$', user_id))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    user_id = request.form.get("user_id", "")
    password = request.form.get("password", "")

    if not is_valid_id(user_id):
        return render_template("message.html",
                               title="שגיאה בהרשמה",
                               message='ת"ז חייבת להכיל בדיוק 9 ספרות.',
                               link_url="/register",
                               link_text="חזרה למסך הרשמה",
                               is_error=True)

    if user_id in users:
        return render_template("message.html",
                               title="שגיאה בהרשמה",
                               message="משתמש עם תעודת זהות זו כבר קיים.",
                               link_url="/register",
                               link_text="חזרה למסך הרשמה",
                               is_error=True)

    users[user_id] = password
    if user_id not in user_history_data:
        user_history_data[user_id] = []

    return render_template("message.html",
                           title="נרשמת בהצלחה!",
                           message="המשתמש נוצר בהצלחה.",
                           link_url="/login",
                           link_text="התחבר עכשיו",
                           is_error=False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    user_id = request.form.get("user_id", "")
    password = request.form.get("password", "")

    if not is_valid_id(user_id):
        return render_template("message.html",
                               title="שגיאה בהתחברות",
                               message='ת"ז חייבת להכיל בדיוק 9 ספרות.',
                               link_url="/login",
                               link_text="חזרה למסך התחברות",
                               is_error=True)

    if users.get(user_id) == password:
        session['user_id'] = user_id
        return redirect(url_for("home"))
    else:
        return render_template("message.html",
                               title="שגיאה בהתחברות",
                               message="שם המשתמש או הסיסמה אינם נכונים.",
                               link_url="/login",
                               link_text="חזרה למסך התחברות",
                               is_error=True)

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return render_template("message.html",
                           title="התנתקת בהצלחה",
                           message="התנתקת מהמערכת בהצלחה.",
                           link_url="/login",
                           link_text="התחבר מחדש",
                           is_error=False)

@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/history")
@login_required
def history():
    user_id = session['user_id']
    if user_id not in user_history_data:
        user_history_data[user_id] = []
    return render_template("history.html", history_data=user_history_data[user_id])

@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
    user_id = session['user_id']
    if request.method == "GET":
        return render_template("calculator.html")
    
    # כאן תוכל להוסיף חישובים זמניים לזיכרון אם תרצה
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_item = {
        "datetime": now_str,
        "note": "חישוב בוצע (דוגמה)"
    }
    user_history_data[user_id].append(history_item)
    return redirect(url_for("history"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
