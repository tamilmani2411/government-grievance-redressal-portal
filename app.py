from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "grievance_secret_key_2026"

# -----------------------------
# Upload Configuration
# -----------------------------
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------
# Database Initialization
# -----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    # Grievances table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS grievances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            photo TEXT,
            status TEXT DEFAULT 'Pending'
        )
        """
    )

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Home Page
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -----------------------------
# Citizen Registration
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, email, username, password) VALUES (?, ?, ?, ?)",
                (name, email, username, password),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists!"

        conn.close()
        return redirect("/login")

    return render_template("register.html")

# -----------------------------
# Citizen Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password),
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["username"] = username
            return redirect("/dashboard")
        else:
            return "Invalid username or password"

    return render_template("login.html")

# -----------------------------
# Citizen Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        username=session["username"],
    )

# -----------------------------
# Report Grievance
# -----------------------------
@app.route("/report", methods=["GET", "POST"])
def report():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        category = request.form["category"]
        location = request.form["location"]
        description = request.form["description"]

        filename = None

        if "photo" in request.files:
            photo = request.files["photo"]
            if photo.filename != "" and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO grievances
            (username, category, location, description, photo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["username"],
                category,
                location,
                description,
                filename,
            ),
        )

        conn.commit()
        conn.close()

        return redirect("/my_grievances")

    return render_template("report.html")

# -----------------------------
# My Grievances
# -----------------------------
@app.route("/my_grievances")
def my_grievances():
    if "username" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT category, location, description, status, photo
        FROM grievances
        WHERE username=?
        ORDER BY id DESC
        """,
        (session["username"],),
    )

    grievances = cursor.fetchall()
    conn.close()

    return render_template(
        "my_grievances.html",
        grievances=grievances,
        username=session["username"],
    )

# -----------------------------
# Admin Login
# -----------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/admin_dashboard")
        else:
            return "Invalid admin credentials"

    return render_template("admin_login.html")

# -----------------------------
# Admin Dashboard
# -----------------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, username, category, location,
               description, status, photo
        FROM grievances
        ORDER BY id DESC
        """
    )

    grievances = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM grievances")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM grievances WHERE status='Pending'"
    )
    pending = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM grievances WHERE status='In Progress'"
    )
    progress = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM grievances WHERE status='Resolved'"
    )
    resolved = cursor.fetchone()[0]

    cursor.execute(
        "SELECT category, COUNT(*) FROM grievances GROUP BY category"
    )

    category_data = cursor.fetchall()

    categories = [row[0] for row in category_data]
    category_counts = [row[1] for row in category_data]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        grievances=grievances,
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved,
        categories=categories,
        category_counts=category_counts,
    )

# -----------------------------
# Update Status
# -----------------------------
@app.route("/update_status/<int:grievance_id>", methods=["POST"])
def update_status(grievance_id):
    if "admin" not in session:
        return redirect("/admin")

    new_status = request.form["status"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE grievances SET status=? WHERE id=?",
        (new_status, grievance_id),
    )

    conn.commit()
    conn.close()

    return redirect("/admin_dashboard")

# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)