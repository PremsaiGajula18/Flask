"""
Prototype demonstrating Python wrapping concepts (Decorators) in Flask:
1. Public Route       -> Unrestricted access
2. Protected Route    -> @login_required decorator wrapper
3. Role-Based Route   -> @role_required('admin') parameterized decorator wrapper
"""

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

app = Flask(__name__)
app.secret_key = "simple-prototype-secret-key"

# Simple in-memory user database for quick testing
USERS = {
    "alice": {"password": "123", "role": "user", "name": "Alice Normal"},
    "admin": {"password": "admin", "role": "admin", "name": "Super Admin"}
}


# ==========================================
# 1. WRAPPER CONCEPTS (CUSTOM DECORATORS)
# ==========================================

def login_required(f):
    """
    Wrapper 1: Requires any logged-in user.
    - @wraps(f) preserves the original function's name and docstring.
    - If user is not in session, redirects to login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Access denied! Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(required_role):
    """
    Wrapper 2: Parameterized decorator for specific user roles (e.g. 'admin').
    - Takes a parameter (required_role) and returns the actual decorator.
    - Checks both login status AND user role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "username" not in session:
                flash("Access denied! Please log in first.", "warning")
                return redirect(url_for("login"))
            
            user_role = session.get("role")
            if user_role != required_role:
                flash(f"Unauthorized! You need '{required_role}' privileges to access this page.", "danger")
                return redirect(url_for("dashboard"))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==========================================
# 2. THREE TYPES OF ROUTES
# ==========================================

# TYPE 1: PUBLIC ROUTE (No wrapper needed)
@app.route("/")
def home():
    return render_template("home.html")


# TYPE 2: PROTECTED ROUTE (@login_required wrapper)
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=session.get("name"), role=session.get("role"))


# TYPE 3: ROLE-RESTRICTED ROUTE (@role_required wrapper)
@app.route("/admin")
@role_required("admin")
def admin_panel():
    return render_template("admin.html", users=USERS)


# ==========================================
# 3. AUTHENTICATION (LOGIN & LOGOUT)
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = USERS.get(username)
        if user and user["password"] == password:
            # Save user session
            session["username"] = username
            session["role"] = user["role"]
            session["name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
