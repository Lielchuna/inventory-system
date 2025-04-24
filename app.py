from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from functools import wraps
import re
import pyodbc

# חיבור ל-SQL Server
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\\SQLEXPRESS;'  # השתמש ב-backslash כפול
    'DATABASE=project;'  # ודא שהדאטה בייס קיים
    'Trusted_Connection=yes;'
)

cursor = conn.cursor()

# הגדרת האפליקציה של Flask
app = Flask(__name__)
app.secret_key = "secret_key_for_session"

# מילון משתמשים: ת"ז -> סיסמה
users = {
    "123456789": "pass123"
}

# היסטוריה לפי משתמש
user_history_data = {}

def is_valid_id(user_id):
    """ ת"ז חייבת להיות בדיוק 9 ספרות """
    return bool(re.match(r'^\d{9}$', user_id))

def login_required(f):
    """ דקורטור - דורש התחברות """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def add_user_to_db(user_id, password):
    """ פונקציה להוספת משתמש חדש לדאטה בייס """
    cursor.execute("INSERT INTO Users (user_id, password) VALUES (?, ?)", (user_id, password))
    conn.commit()

def add_order_to_db(user_id, num_products, num_months):
    """ פונקציה להוספת הזמנה לדאטה בייס ומחזירה את ה-ID שלה """
    try:
        cursor.execute("""
            INSERT INTO OrderHistory (user_id, datetime, num_products, num_months) 
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?)
        """, (user_id, datetime.now(), num_products, num_months))
        order_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Order added successfully with ID: {order_id}")  # דיבוג
        return order_id
    except Exception as e:
        print(f"Error adding order to database: {e}")  # דיבוג
        conn.rollback()
        return None


def add_product_details_to_db(order_id, product_name, initial_inventory, storage_cost,
                              max_production_capacity, max_inventory, monthly_production_costs, demands):
    """ פונקציה להוספת פרטי מוצר לדאטה בייס """
    try:
        print(f"Attempting to insert product details. Order ID: {order_id}, Product Name: {product_name}")
        cursor.execute("""
            INSERT INTO ProductDetails (
                order_id, product_name, initial_inventory, storage_cost,
                max_production_capacity, max_inventory, monthly_production_costs, demands
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, 
            product_name, 
            initial_inventory, 
            storage_cost, 
            max_production_capacity, 
            max_inventory, 
            ','.join(map(str, monthly_production_costs)), 
            ','.join(map(str, demands))
        ))
        conn.commit()
        print("Product details inserted successfully.")
    except Exception as e:
        print(f"Failed to insert product details: {e}")
        conn.rollback()



def check_order_exists(order_id):
    """ פונקציה לבדוק אם הזמנה קיימת בטבלת OrderHistory """
    cursor.execute("SELECT id FROM OrderHistory WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if order:
        print(f"Order ID {order_id} exists in OrderHistory.")
    else:
        print(f"Order ID {order_id} does not exist in OrderHistory.")
    return order is not None

@app.route("/register", methods=["GET", "POST"])
def register():
    """ עמוד הרשמה למשתמש חדש """
    if request.method == "GET":
        return render_template("register.html")

    else:
        user_id = request.form.get("user_id", "")
        password = request.form.get("password", "")

        if not is_valid_id(user_id):
            return render_template(
                "message.html",
                title="שגיאה בהרשמה",
                message='ת"ז חייבת להכיל בדיוק 9 ספרות.',
                link_url="/register",
                link_text="חזרה למסך הרשמה",
                is_error=True
            )

        # בדוק אם המשתמש קיים כבר בדאטה בייס
        cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            return render_template(
                "message.html",
                title="שגיאה בהרשמה",
                message="משתמש עם תעודת זהות זו כבר קיים.",
                link_url="/register",
                link_text="חזרה למסך הרשמה",
                is_error=True
            )

        # הוסף את המשתמש לדאטה בייס
        add_user_to_db(user_id, password)

        # הוספת המשתמש למילון היסטוריית המשתמשים
        if user_id not in user_history_data:
            user_history_data[user_id] = []  # אם לא קיים, הוסף רשימה ריקה

        return render_template(
            "message.html",
            title="נרשמת בהצלחה!",
            message="המשתמש נוצר בהצלחה.",
            link_url="/login",
            link_text="התחבר עכשיו",
            is_error=False
        )


@app.route("/login", methods=["GET", "POST"])
def login():
    """ עמוד התחברות """
    if request.method == "GET":
        return render_template("login.html")
    else:
        user_id = request.form.get("user_id", "")
        password = request.form.get("password", "")

        # בדיקת ת"ז
        if not is_valid_id(user_id):
            return render_template(
                "message.html",
                title="שגיאה בהתחברות",
                message="ת\"ז חייבת להיות בדיוק 9 ספרות.",
                link_url="/login",
                link_text="חזרה למסך התחברות",
                is_error=True
            )

        # בדיקת שם משתמש/סיסמה בדאטה בייס
        cursor.execute("SELECT * FROM Users WHERE user_id = ? AND password = ?", (user_id, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user_id
            return redirect(url_for("home"))
        else:
            return render_template(
                "message.html",
                title="שגיאה בהתחברות",
                message="שם המשתמש או הסיסמה אינם נכונים.",
                link_url="/login",
                link_text="חזרה למסך התחברות",
                is_error=True
            )


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return render_template(
        "message.html",
        title="התנתקת בהצלחה",
        message="התנתקת מהמערכת בהצלחה.",
        link_url="/login",
        link_text="התחבר מחדש",
        is_error=False
    )


def calculate_optimal_inventory(num_months, initial_inventory, storage_cost,
                                monthly_production_costs, max_production_capacity,
                                max_inventory, demands):
    """ חישוב DP למוצר יחיד (כמו קודם) """
    dp = [[float('inf')] * (max_inventory + 1) for _ in range(num_months + 1)]
    decisions = [[0] * (max_inventory + 1) for _ in range(num_months + 1)]

    if initial_inventory <= max_inventory:
        dp[0][initial_inventory] = 0
    else:
        return None

    for month in range(1, num_months + 1):
        for current_inventory in range(max_inventory + 1):
            if dp[month - 1][current_inventory] == float('inf'):
                continue

            for order in range(max_production_capacity + 1):
                if current_inventory + order > max_inventory:
                    break

                remaining_inventory = current_inventory + order - demands[month - 1]
                if remaining_inventory < 0:
                    continue

                cost_prod = order * monthly_production_costs[month - 1]
                cost_store = remaining_inventory * storage_cost
                cost = dp[month - 1][current_inventory] + cost_prod + cost_store

                if cost < dp[month][remaining_inventory]:
                    dp[month][remaining_inventory] = cost
                    decisions[month][remaining_inventory] = order

    min_cost = min(dp[num_months])
    if min_cost == float('inf'):
        return None

    best_inventory = dp[num_months].index(min_cost)
    orders = []
    inventories = []

    for month in range(num_months, 0, -1):
        order = decisions[month][best_inventory]
        orders.append(order)
        inventories.append(best_inventory)
        best_inventory = best_inventory + demands[month - 1] - order

    orders.reverse()
    inventories.reverse()

    return {
        "min_cost": min_cost,
        "orders": orders,
        "inventories": inventories
    }


@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/history")
@login_required
def history():
    user_id = session['user_id']
    
    # ודא שהמפתח קיים במילון לפני שאתה ניגש אליו
    if user_id not in user_history_data:
        user_history_data[user_id] = []  # אם לא קיים, הוסף רשימה ריקה

    my_history = user_history_data[user_id]
    return render_template("history.html", history_data=my_history)

@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
    user_id = session['user_id']
    if request.method == "GET":
        return '''
        <!DOCTYPE html>
        <html lang="he">
        <head>
            <meta charset="UTF-8" />
            <title>מחשבון הזמנה - מספר מוצרים</title>
            <style>
                body { direction: rtl; font-family: Arial, sans-serif; margin: 50px; background-color: #f0f2f5; }
                label { display: block; margin-top: 10px; }
                input { width: 200px; }
                button { margin-top: 20px; padding: 10px; cursor: pointer; }
                a { margin-top: 20px; display: inline-block; }
                .box {
                    max-width: 400px; 
                    margin: 50px auto; 
                    background: #fff; 
                    padding: 20px; 
                    border-radius: 8px; 
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
                .btn {
                    background-color: #4CAF50;
                    color: #fff;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 15px;
                }
                .btn:hover {
                    background-color: #45a049;
                }
                h1 { text-align: center; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>מחשבון הזמנה - הזן מספר מוצרים</h1>
                <form method="POST" action="/calculator">
                    <label>מספר מוצרים:
                        <input type="number" name="num_products" min="1" required>
                    </label>
                    <label>מספר חודשים לתכנון:
                        <input type="number" name="num_months" min="1" required>
                    </label>
                    <br>
                    <p>לאחר מילוי הנתונים לחץ על "המשך"</p>
                    <button type="submit" name="phase" value="phase1" class="btn">המשך</button>
                </form>
                <br>
                <a href="/">חזרה לדף הראשי</a>
            </div>
        </body>
        </html>
        '''
    phase = request.form.get("phase")
    if phase == "phase1":
        num_products = int(request.form["num_products"])
        num_months = int(request.form["num_months"])

        # ודא שהמשתמש קיים במילון היסטוריית המשתמשים
        if user_id not in user_history_data:
            user_history_data[user_id] = []  # אם לא קיים, הוסף רשימה ריקה

        # הוסף הזמנה לדאטה בייס
        add_order_to_db(user_id, num_products, num_months)
        return render_template("multi_products_form.html",
                               num_products=num_products,
                               num_months=num_months)
    else:
        # phase2
        num_products = int(request.form["num_products"])
        num_months = int(request.form["num_months"])
        products_results = []

        for p in range(1, num_products + 1):
            product_name = request.form[f"product_name_{p}"]
            initial_inventory = int(request.form[f"initial_inventory_{p}"])
            storage_cost = float(request.form[f"storage_cost_{p}"])
            max_production_capacity = int(request.form[f"max_production_capacity_{p}"])
            max_inventory = int(request.form[f"max_inventory_{p}"])
            monthly_costs_str = request.form[f"monthly_production_costs_{p}"]
            demands_str = request.form[f"demands_{p}"]

            monthly_costs = [float(x) for x in monthly_costs_str.split(",")]
            demands = [int(x) for x in demands_str.split(",")]

            result_data = calculate_optimal_inventory(
                num_months=num_months,
                initial_inventory=initial_inventory,
                storage_cost=storage_cost,
                monthly_production_costs=monthly_costs,
                max_production_capacity=max_production_capacity,
                max_inventory=max_inventory,
                demands=demands
            )

            if not result_data:
                product_res = {
                    "product_name": product_name,
                    "initial_inventory": initial_inventory,
                    "storage_cost": storage_cost,
                    "max_production_capacity": max_production_capacity,
                    "max_inventory": max_inventory,
                    "monthly_production_costs": monthly_costs,
                    "demands": demands,
                    "found_solution": False,
                    "min_cost": None,
                    "orders": [],
                    "inventories": []
                }
            else:
                product_res = {
                    "product_name": product_name,
                    "initial_inventory": initial_inventory,
                    "storage_cost": storage_cost,
                    "max_production_capacity": max_production_capacity,
                    "max_inventory": max_inventory,
                    "monthly_production_costs": monthly_costs,
                    "demands": demands,
                    "found_solution": True,
                    "min_cost": result_data["min_cost"],
                    "orders": result_data["orders"],
                    "inventories": result_data["inventories"]
                }

                # הוספת פרטי המוצר לטבלת ProductDetails
                if user_history_data[user_id]:
                    order_id = user_history_data[user_id][-1]["datetime"]  # מקבלים את מזהה ההזמנה האחרון
                    add_product_details_to_db(order_id, product_name, initial_inventory, storage_cost, max_production_capacity, max_inventory, monthly_costs, demands)

            products_results.append(product_res)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_item = {
            "datetime": now_str,
            "num_products": num_products,
            "num_months": num_months,
            "products": products_results
        }

        # ודא שהמשתמש קיים במילון היסטוריית המשתמשים
        if user_id not in user_history_data:
            user_history_data[user_id] = []  # אם לא קיים, הוסף רשימה ריקה

        user_history_data[user_id].append(history_item)
        idx = len(user_history_data[user_id]) - 1
        return redirect(url_for("result", idx=idx))


@app.route("/result")
@login_required
def result():
    user_id = session['user_id']
    idx = request.args.get("idx")
    if idx is None:
        return render_template(
            "message.html",
            title="שגיאה",
            message="לא נבחרה תוצאה להצגה.",
            link_url="/history",
            link_text="חזרה להיסטוריה",
            is_error=True
        )

    idx = int(idx)
    my_history = user_history_data[user_id]
    if idx < 0 or idx >= len(my_history):
        return render_template(
            "message.html",
            title="שגיאה",
            message="אינדקס מחוץ לטווח.",
            link_url="/history",
            link_text="חזרה להיסטוריה",
            is_error=True
        )

    item = my_history[idx]
    return render_template("result.html", item=item)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

