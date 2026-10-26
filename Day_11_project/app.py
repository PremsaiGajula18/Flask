"""
=============================================================================
Trip Planner — Full-Stack Travel Itinerary & Budgeting Web Application
=============================================================================
Application Controller: app.py

Features:
---------
- Single-file consolidated architecture (similar to DAY-10_PROJECT).
- MySQL relational database integration using mysql-connector-python.
- Parameterized SQL queries preventing SQL injection vulnerabilities.
- User authentication with Flask sessions and Werkzeug password hashing.
- Cryptographic CSRF protection enforced across all state-changing POST requests.
- Strict user-scoping for private trips and daily itinerary activities.
- Automatic live budget recalculation (total cost, remaining / exceeded status).
- Validation preventing date collisions or editing trip dates when activities exist.
- Public destination exploration with combined place name and category filters.
=============================================================================
"""

import datetime
from decimal import Decimal, InvalidOperation
import functools
import os
import re
import secrets
from typing import Any, Callable, Dict, List, Optional, Tuple

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import mysql.connector
from mysql.connector import Error, MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
# Flask Application Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Secret key used for session signing and cryptographic cookies
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "trip-planner-adventures-session-secret-key-2026"
)

# ---------------------------------------------------------------------------
# MySQL Database Configuration Parameters
# ---------------------------------------------------------------------------
MYSQL_HOST: str = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER: str = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD: str = os.environ.get("MYSQL_PASSWORD", "premsai444@123")
MYSQL_DATABASE: str = os.environ.get("MYSQL_DATABASE", "trip_planner_db")

# Allowed activity categories enforced across forms
ACTIVITY_CATEGORIES: Tuple[str, ...] = (
    "Sightseeing",
    "Food",
    "Adventure",
    "Shopping",
    "Nature",
    "Culture",
    "Accommodation",
    "Transportation",
    "Other",
)


def get_db() -> MySQLConnection:
    """
    Establish and retrieve the current request's MySQL database connection.

    Stores connection in Flask's application context `g` to maintain a single
    connection per request cycle.
    """
    if "db" not in g:
        try:
            g.db = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
                autocommit=False,
            )
        except Error as err:
            app.logger.error(f"MySQL Connection Error: {err}")
            raise err
    return g.db


def close_db(e=None) -> None:
    """Cleanly close the active MySQL connection at the end of the request context."""
    db = g.pop("db", None)
    if db is not None and db.is_connected():
        db.close()


app.teardown_appcontext(close_db)


# ---------------------------------------------------------------------------
# Security & CSRF Protection Layer
# ---------------------------------------------------------------------------
def generate_csrf_token() -> str:
    """
    Generate or retrieve a cryptographically secure per-session CSRF token.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


class CurrentUserProxy:
    """
    Proxy helper object mimicking Flask-Login's current_user in templates.
    Ensures templates using current_user.is_authenticated and current_user.username
    continue to work seamlessly with native Flask sessions.
    """
    @property
    def is_authenticated(self) -> bool:
        return "user_id" in session

    @property
    def id(self) -> Optional[int]:
        return session.get("user_id")

    @property
    def username(self) -> Optional[str]:
        return session.get("username")


current_user = CurrentUserProxy()


@app.context_processor
def inject_csrf_and_globals() -> Dict[str, Any]:
    """
    Inject global utilities into all Jinja2 template contexts.
    """
    return {
        "csrf_token": generate_csrf_token,
        "current_user": current_user,
        "now_year": datetime.datetime.now().year,
        "categories": ACTIVITY_CATEGORIES,
    }


@app.before_request
def verify_csrf_token() -> Optional[Any]:
    """
    Verify CSRF tokens on all state-mutating HTTP POST requests.
    """
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token")
        expected_token = session.get("csrf_token")

        if not submitted_token or submitted_token != expected_token:
            flash("Security check failed (invalid or missing CSRF token). Please try again.", "danger")
            return redirect(request.referrer or url_for("home"))
    return None


def login_required(view: Callable) -> Callable:
    """
    Decorator to restrict access to authenticated users only.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return view(**kwargs)

    return wrapped_view


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    """Render custom 404 Not Found error template."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Render custom 500 Internal Server Error template."""
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Authentication Routes (Register, Login, Logout)
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handle user registration with form validation and password hashing.
    """
    if current_user.is_authenticated:
        return redirect(url_for("my_trips"))

    errors: Dict[str, str] = {}
    form_data: Dict[str, str] = {}

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        form_data["username"] = username

        # Validate username
        if not username:
            errors["username"] = "Username is required."
        elif len(username) < 3 or len(username) > 50:
            errors["username"] = "Username must be between 3 and 50 characters."
        else:
            try:
                db_conn = get_db()
                cursor = db_conn.cursor(dictionary=True)
                cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", (username,))
                if cursor.fetchone():
                    errors["username"] = "That username is already taken. Please choose another."
                cursor.close()
            except Error as err:
                app.logger.error(f"Database error during registration check: {err}")
                errors["username"] = "A database error occurred. Please try again."

        # Validate password
        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters long."

        # Validate password confirmation
        if not confirm_password:
            errors["confirm_password"] = "Please confirm your password."
        elif password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        # Create user record
        if not errors:
            pwd_hash = generate_password_hash(password)
            try:
                db_conn = get_db()
                cursor = db_conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, pwd_hash),
                )
                db_conn.commit()
                cursor.close()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("login"))
            except Error as err:
                db_conn.rollback()
                app.logger.error(f"User registration insert error: {err}")
                errors["username"] = "Failed to create user. Please choose another username."

    return render_template("register.html", errors=errors, form_data=form_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle user login, credential verification, and session creation.
    """
    if current_user.is_authenticated:
        return redirect(url_for("my_trips"))

    errors: Dict[str, str] = {}
    form_data: Dict[str, str] = {}

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        form_data["username"] = username

        if not username:
            errors["username"] = "Username is required."
        if not password:
            errors["password"] = "Password is required."

        if not errors:
            try:
                db_conn = get_db()
                cursor = db_conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, username, password_hash FROM users WHERE username = %s LIMIT 1",
                    (username,),
                )
                user = cursor.fetchone()
                cursor.close()

                if not user:
                    errors["username"] = "User does not exist. Please check your username."
                elif not check_password_hash(user["password_hash"], password):
                    errors["password"] = "Incorrect password. Please try again."
                else:
                    session.clear()
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    session["csrf_token"] = secrets.token_hex(24)

                    flash(f"Welcome back, {user['username']}!", "success")
                    next_page = request.args.get("next")
                    if next_page and next_page.startswith("/"):
                        return redirect(next_page)
                    return redirect(url_for("my_trips"))
            except Error as err:
                app.logger.error(f"Login database error: {err}")
                errors["general"] = "Database connection error. Please try again."

    return render_template("login.html", errors=errors, form_data=form_data)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    Terminate authenticated session and redirect to the home page.
    """
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Public Routes (Home, Explore)
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Page 1: Home landing page with hero, features, and sample destinations."""
    featured_places = []
    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM place_suggestions LIMIT 4")
        featured_places = cursor.fetchall()
        cursor.close()
    except Error as err:
        app.logger.error(f"Home page fetch error: {err}")

    return render_template("home.html", featured_places=featured_places)


@app.route("/explore")
def explore():
    """Page 8: Public place suggestions with combined search, destination, and category filtering."""
    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()
    selected_destination = request.args.get("destination", "").strip()

    sql = "SELECT * FROM place_suggestions WHERE 1=1"
    params = []

    # Combined Search, Destination, and Category Filters
    if search_query:
        sql += " AND name LIKE %s"
        params.append(f"%{search_query}%")

    if selected_category:
        sql += " AND category = %s"
        params.append(selected_category)

    if selected_destination:
        sql += " AND destination = %s"
        params.append(selected_destination)

    sql += " ORDER BY name ASC"

    places = []
    destinations = []
    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(sql, tuple(params))
        places = cursor.fetchall()

        cursor.execute("SELECT DISTINCT destination FROM place_suggestions ORDER BY destination ASC")
        dest_rows = cursor.fetchall()
        destinations = [d["destination"] for d in dest_rows if d.get("destination")]
        cursor.close()
    except Error as err:
        app.logger.error(f"Explore places error: {err}")

    return render_template(
        "explore.html",
        places=places,
        search_query=search_query,
        selected_category=selected_category,
        selected_destination=selected_destination,
        categories=ACTIVITY_CATEGORIES,
        destinations=destinations,
    )


# ---------------------------------------------------------------------------
# Helper: Format Trip Dictionary with Business Logic Calculations
# ---------------------------------------------------------------------------
def format_trip_item(trip: Dict[str, Any], total_cost: Decimal) -> Dict[str, Any]:
    """
    Decorate a trip dictionary with financial and duration properties
    matching what Jinja templates expect.
    """
    budget = Decimal(str(trip["budget"])) if trip["budget"] is not None else Decimal("0.00")
    start_date = trip["start_date"]
    end_date = trip["end_date"]

    # Calculate duration
    if isinstance(start_date, (datetime.date, datetime.datetime)) and isinstance(end_date, (datetime.date, datetime.datetime)):
        duration_days = (end_date - start_date).days + 1
    else:
        duration_days = 0

    diff = budget - total_cost

    if diff > 0:
        status_text = "Budget Remaining"
        status_class = "status-remaining"
    elif diff == 0:
        status_text = "Budget Fully Used"
        status_class = "status-used"
    else:
        status_text = "Budget Exceeded"
        status_class = "status-exceeded"

    if budget <= 0:
        utilization_pct = 100.0 if total_cost > 0 else 0.0
    else:
        utilization_pct = round(float((total_cost / budget) * 100), 1)

    return {
        "id": trip["id"],
        "owner_id": trip["owner_id"],
        "destination": trip["destination"],
        "start_date": start_date,
        "end_date": end_date,
        "budget": budget,
        "total_cost": total_cost,
        "duration_days": duration_days,
        "budget_difference": diff,
        "budget_status": status_text,
        "budget_status_class": status_class,
        "utilization_percentage": utilization_pct,
    }


# ---------------------------------------------------------------------------
# Trip Management Routes (My Trips, Create, Detail, Edit, Delete)
# ---------------------------------------------------------------------------
@app.route("/trips")
@login_required
def my_trips():
    """Page 4: List trips belonging exclusively to the current logged-in user."""
    user_id = session["user_id"]
    trips_list = []

    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT t.*, COALESCE(SUM(a.cost), 0.00) AS total_activity_cost
            FROM trips t
            LEFT JOIN activities a ON t.id = a.trip_id
            WHERE t.owner_id = %s
            GROUP BY t.id
            ORDER BY t.start_date ASC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        cursor.close()

        for row in rows:
            cost = Decimal(str(row["total_activity_cost"]))
            trips_list.append(format_trip_item(row, cost))
    except Error as err:
        app.logger.error(f"My Trips query error: {err}")
        flash("Could not load trips at this time.", "danger")

    return render_template("my_trips.html", trips=trips_list)


@app.route("/trips/create", methods=["GET", "POST"])
@login_required
def create_trip():
    """Page 5: Create a new trip with input validation and location auto-fill."""
    user_id = session["user_id"]
    errors: Dict[str, str] = {}
    form_data: Dict[str, str] = {}

    if request.method == "POST":
        destination = request.form.get("destination", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        budget_str = request.form.get("budget", "").strip()
        place_name = request.form.get("place_name", "").strip()
        place_category = request.form.get("place_category", "").strip()
        add_activity = request.form.get("add_activity", "").strip()

        form_data = {
            "destination": destination,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "budget": budget_str,
            "place_name": place_name,
            "place_category": place_category,
            "add_activity": add_activity,
        }

        # Destination validation
        if not destination:
            errors["destination"] = "Destination is required."

        # Date validations
        start_date = None
        if not start_date_str:
            errors["start_date"] = "Start date is required."
        else:
            try:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors["start_date"] = "Invalid start date format (YYYY-MM-DD)."

        end_date = None
        if not end_date_str:
            errors["end_date"] = "End date is required."
        else:
            try:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors["end_date"] = "Invalid end date format (YYYY-MM-DD)."

        if start_date and end_date and end_date < start_date:
            errors["end_date"] = "End date cannot be earlier than start date."

        # Budget validation
        budget = None
        if not budget_str:
            errors["budget"] = "Total budget is required."
        else:
            try:
                budget = Decimal(budget_str)
                if budget < 0:
                    errors["budget"] = "Budget cannot be negative."
            except (InvalidOperation, ValueError):
                errors["budget"] = "Budget must be a valid numeric value."

        if not errors:
            try:
                db_conn = get_db()
                cursor = db_conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO trips (owner_id, destination, start_date, end_date, budget)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, destination, start_date, end_date, budget),
                )
                trip_id = cursor.lastrowid

                # Automatically add the selected explore place to activities if requested
                if place_name and (add_activity in ("1", "true", "on")):
                    valid_cat = place_category if place_category in ACTIVITY_CATEGORIES else "Sightseeing"
                    cursor.execute(
                        """
                        INSERT INTO activities (trip_id, name, activity_date, activity_time, category, place, cost)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            trip_id,
                            place_name,
                            start_date,
                            "10:00:00",
                            valid_cat,
                            destination,
                            Decimal("0.00"),
                        ),
                    )

                db_conn.commit()
                cursor.close()
                if place_name and (add_activity in ("1", "true", "on")):
                    flash(f"Trip to {destination} created successfully with '{place_name}' added to your itinerary!", "success")
                else:
                    flash(f"Trip to {destination} created successfully!", "success")
                return redirect(url_for("trip_detail", trip_id=trip_id))
            except Error as err:
                db_conn.rollback()
                app.logger.error(f"Error creating trip: {err}")
                errors["general"] = "Failed to create trip due to database error."
    else:
        # Pre-fill form from query parameters when selecting a location from explore page
        preset_destination = request.args.get("destination", "").strip()
        preset_place = request.args.get("place_name", "").strip()
        preset_category = request.args.get("category", "").strip()
        preset_budget = request.args.get("budget", "").strip()
        preset_start_date = request.args.get("start_date", "").strip()
        preset_end_date = request.args.get("end_date", "").strip()

        if preset_destination or preset_place:
            today = datetime.date.today()
            default_start = (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            default_end = (today + datetime.timedelta(days=14)).strftime("%Y-%m-%d")

            form_data = {
                "destination": preset_destination,
                "start_date": preset_start_date or default_start,
                "end_date": preset_end_date or default_end,
                "budget": preset_budget or "1500.00",
                "place_name": preset_place,
                "place_category": preset_category,
                "add_activity": "1",
            }

    return render_template("trip_form.html", is_edit=False, errors=errors, form_data=form_data)


@app.route("/trips/<int:trip_id>")
@login_required
def trip_detail(trip_id: int):
    """Page 6: Trip dashboard displaying daily itinerary and recalculating budget metrics."""
    user_id = session["user_id"]

    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)

        # Strict user-scoping: owner_id check ensures other users cannot access this trip
        cursor.execute(
            "SELECT * FROM trips WHERE id = %s AND owner_id = %s LIMIT 1",
            (trip_id, user_id),
        )
        trip_row = cursor.fetchone()

        if not trip_row:
            cursor.close()
            abort(404)

        # Retrieve all activities for this trip sorted chronologically
        cursor.execute(
            """
            SELECT * FROM activities
            WHERE trip_id = %s
            ORDER BY activity_date ASC, activity_time ASC
            """,
            (trip_id,),
        )
        activities = cursor.fetchall()
        cursor.close()

        # Compute total cost
        total_cost = Decimal("0.00")
        itinerary_by_date = {}

        for act in activities:
            cost = Decimal(str(act["cost"])) if act["cost"] is not None else Decimal("0.00")
            act["cost"] = cost
            total_cost += cost

            # Format activity time for Jinja display if stored as timedelta
            if isinstance(act["activity_time"], datetime.timedelta):
                total_sec = int(act["activity_time"].total_seconds())
                hrs = total_sec // 3600
                mins = (total_sec % 3600) // 60
                act["activity_time"] = datetime.time(hrs, mins)

            act_date = act["activity_date"]
            if act_date not in itinerary_by_date:
                itinerary_by_date[act_date] = []
            itinerary_by_date[act_date].append(act)

        # Sorted list of tuples: [(date, [activities...]), ...]
        sorted_itinerary = sorted(itinerary_by_date.items(), key=lambda x: x[0])
        trip = format_trip_item(trip_row, total_cost)

        return render_template(
            "trip_detail.html",
            trip=trip,
            itinerary=sorted_itinerary,
            total_activities_count=len(activities),
        )
    except Error as err:
        app.logger.error(f"Trip detail error: {err}")
        abort(500)


@app.route("/trips/<int:trip_id>/edit", methods=["GET", "POST"])
@login_required
def edit_trip(trip_id: int):
    """Page 5: Edit an existing trip. Validates date bounds against existing activities."""
    user_id = session["user_id"]
    errors: Dict[str, str] = {}

    db_conn = get_db()
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM trips WHERE id = %s AND owner_id = %s LIMIT 1",
        (trip_id, user_id),
    )
    trip_row = cursor.fetchone()

    if not trip_row:
        cursor.close()
        abort(404)

    if request.method == "GET":
        form_data = {
            "destination": trip_row["destination"],
            "start_date": trip_row["start_date"].strftime("%Y-%m-%d"),
            "end_date": trip_row["end_date"].strftime("%Y-%m-%d"),
            "budget": str(trip_row["budget"]),
        }
        cursor.close()
    else:
        destination = request.form.get("destination", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        budget_str = request.form.get("budget", "").strip()

        form_data = {
            "destination": destination,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "budget": budget_str,
        }

        if not destination:
            errors["destination"] = "Destination is required."

        new_start_date = None
        if not start_date_str:
            errors["start_date"] = "Start date is required."
        else:
            try:
                new_start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors["start_date"] = "Invalid start date format."

        new_end_date = None
        if not end_date_str:
            errors["end_date"] = "End date is required."
        else:
            try:
                new_end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors["end_date"] = "Invalid end date format."

        if new_start_date and new_end_date and new_end_date < new_start_date:
            errors["end_date"] = "End date cannot be earlier than start date."

        new_budget = None
        if not budget_str:
            errors["budget"] = "Total budget is required."
        else:
            try:
                new_budget = Decimal(budget_str)
                if new_budget < 0:
                    errors["budget"] = "Budget cannot be negative."
            except (InvalidOperation, ValueError):
                errors["budget"] = "Budget must be a valid numeric value."

        # Business Rule 5: Prevent date changes that leave existing activities outside updated period
        if new_start_date and new_end_date and not errors.get("start_date") and not errors.get("end_date"):
            cursor.execute(
                """
                SELECT name, activity_date FROM activities
                WHERE trip_id = %s AND (activity_date < %s OR activity_date > %s)
                """,
                (trip_id, new_start_date, new_end_date),
            )
            conflicting_activities = cursor.fetchall()

            if conflicting_activities:
                conflict_details = [
                    f'"{a["name"]}" on {a["activity_date"].strftime("%Y-%m-%d")}'
                    for a in conflicting_activities
                ]
                errors["general"] = (
                    f"Cannot change trip dates. The following {len(conflicting_activities)} "
                    f"activity(ies) would fall outside the new date range ({new_start_date} to {new_end_date}): "
                    f"{', '.join(conflict_details)}. Please update or delete them first."
                )

        if not errors:
            try:
                cursor.execute(
                    """
                    UPDATE trips
                    SET destination = %s, start_date = %s, end_date = %s, budget = %s
                    WHERE id = %s AND owner_id = %s
                    """,
                    (destination, new_start_date, new_end_date, new_budget, trip_id, user_id),
                )
                db_conn.commit()
                cursor.close()
                flash("Trip updated successfully!", "success")
                return redirect(url_for("trip_detail", trip_id=trip_id))
            except Error as err:
                db_conn.rollback()
                app.logger.error(f"Trip edit update error: {err}")
                errors["general"] = "Database error while updating trip."

        cursor.close()

    trip_item = format_trip_item(trip_row, Decimal("0.00"))
    return render_template("trip_form.html", is_edit=True, trip=trip_item, errors=errors, form_data=form_data)


@app.route("/trips/<int:trip_id>/delete", methods=["POST"])
@login_required
def delete_trip(trip_id: int):
    """Page 4/6: Delete a trip and cascade delete its activities. Restricted to owner."""
    user_id = session["user_id"]

    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT destination FROM trips WHERE id = %s AND owner_id = %s", (trip_id, user_id))
        trip = cursor.fetchone()

        if not trip:
            cursor.close()
            abort(404)

        dest = trip["destination"]
        cursor.execute("DELETE FROM trips WHERE id = %s AND owner_id = %s", (trip_id, user_id))
        db_conn.commit()
        cursor.close()
        flash(f"Trip to {dest} and all associated activities were successfully deleted.", "info")
    except Error as err:
        app.logger.error(f"Delete trip error: {err}")
        flash("Could not delete trip.", "danger")

    return redirect(url_for("my_trips"))


# ---------------------------------------------------------------------------
# Activity Routes (Create, Edit, Delete)
# ---------------------------------------------------------------------------
@app.route("/trips/<int:trip_id>/activities/create", methods=["GET", "POST"])
@login_required
def create_activity(trip_id: int):
    """Page 7: Add a scheduled activity to an owned trip."""
    user_id = session["user_id"]
    errors: Dict[str, str] = {}

    db_conn = get_db()
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE id = %s AND owner_id = %s LIMIT 1", (trip_id, user_id))
    trip_row = cursor.fetchone()

    if not trip_row:
        cursor.close()
        abort(404)

    trip = format_trip_item(trip_row, Decimal("0.00"))
    form_data = {
        "activity_date": trip["start_date"].strftime("%Y-%m-%d"),
        "activity_time": "10:00",
        "category": "Sightseeing",
        "cost": "0.00",
    }

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        date_str = request.form.get("activity_date", "").strip()
        time_str = request.form.get("activity_time", "").strip()
        category = request.form.get("category", "").strip()
        place = request.form.get("place", "").strip()
        cost_str = request.form.get("cost", "").strip()

        form_data = {
            "name": name,
            "activity_date": date_str,
            "activity_time": time_str,
            "category": category,
            "place": place,
            "cost": cost_str,
        }

        if not name:
            errors["name"] = "Activity name is required."

        # Date validation against trip start & end dates
        act_date = None
        if not date_str:
            errors["activity_date"] = "Activity date is required."
        else:
            try:
                act_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if act_date < trip["start_date"] or act_date > trip["end_date"]:
                    errors["activity_date"] = (
                        f"Activity date must fall between trip start date ({trip['start_date']}) "
                        f"and end date ({trip['end_date']})."
                    )
            except ValueError:
                errors["activity_date"] = "Invalid date format (YYYY-MM-DD)."

        # Time validation
        act_time = None
        if not time_str:
            errors["activity_time"] = "Activity time is required."
        else:
            try:
                act_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                try:
                    act_time = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
                except ValueError:
                    errors["activity_time"] = "Invalid time format (HH:MM)."

        if not category or category not in ACTIVITY_CATEGORIES:
            errors["category"] = "Please select a valid category."

        if not place:
            errors["place"] = "Place is required."

        # Cost validation
        act_cost = None
        if not cost_str:
            errors["cost"] = "Estimated cost is required."
        else:
            try:
                act_cost = Decimal(cost_str)
                if act_cost < 0:
                    errors["cost"] = "Activity cost cannot be negative."
            except (InvalidOperation, ValueError):
                errors["cost"] = "Cost must be a valid numeric amount."

        if not errors:
            try:
                cursor.execute(
                    """
                    INSERT INTO activities (trip_id, name, activity_date, activity_time, category, place, cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (trip_id, name, act_date, act_time, category, place, act_cost),
                )
                db_conn.commit()
                cursor.close()
                flash(f'Activity "{name}" added to itinerary!', "success")
                return redirect(url_for("trip_detail", trip_id=trip_id))
            except Error as err:
                db_conn.rollback()
                app.logger.error(f"Error adding activity: {err}")
                errors["general"] = "Database error while adding activity."

    cursor.close()
    return render_template(
        "activity_form.html",
        is_edit=False,
        trip=trip,
        errors=errors,
        form_data=form_data,
        categories=ACTIVITY_CATEGORIES,
    )


@app.route("/activities/<int:activity_id>/edit", methods=["GET", "POST"])
@login_required
def edit_activity(activity_id: int):
    """Page 7: Edit an existing activity and refresh trip budget calculations."""
    user_id = session["user_id"]
    errors: Dict[str, str] = {}

    db_conn = get_db()
    cursor = db_conn.cursor(dictionary=True)

    # Scoped query: verify activity belongs to trip owned by current_user
    cursor.execute(
        """
        SELECT a.*, t.start_date AS trip_start, t.end_date AS trip_end, t.destination AS trip_dest, t.budget AS trip_budget
        FROM activities a
        JOIN trips t ON a.trip_id = t.id
        WHERE a.id = %s AND t.owner_id = %s
        LIMIT 1
        """,
        (activity_id, user_id),
    )
    act_row = cursor.fetchone()

    if not act_row:
        cursor.close()
        abort(404)

    trip = {
        "id": act_row["trip_id"],
        "destination": act_row["trip_dest"],
        "start_date": act_row["trip_start"],
        "end_date": act_row["trip_end"],
        "budget": Decimal(str(act_row["trip_budget"])),
    }

    if request.method == "GET":
        time_val = act_row["activity_time"]
        if isinstance(time_val, datetime.timedelta):
            tot = int(time_val.total_seconds())
            time_str = f"{tot // 3600:02d}:{(tot % 3600) // 60:02d}"
        else:
            time_str = time_val.strftime("%H:%M")

        form_data = {
            "name": act_row["name"],
            "activity_date": act_row["activity_date"].strftime("%Y-%m-%d"),
            "activity_time": time_str,
            "category": act_row["category"],
            "place": act_row["place"],
            "cost": str(act_row["cost"]),
        }
        cursor.close()
    else:
        name = request.form.get("name", "").strip()
        date_str = request.form.get("activity_date", "").strip()
        time_str = request.form.get("activity_time", "").strip()
        category = request.form.get("category", "").strip()
        place = request.form.get("place", "").strip()
        cost_str = request.form.get("cost", "").strip()

        form_data = {
            "name": name,
            "activity_date": date_str,
            "activity_time": time_str,
            "category": category,
            "place": place,
            "cost": cost_str,
        }

        if not name:
            errors["name"] = "Activity name is required."

        act_date = None
        if not date_str:
            errors["activity_date"] = "Activity date is required."
        else:
            try:
                act_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if act_date < trip["start_date"] or act_date > trip["end_date"]:
                    errors["activity_date"] = (
                        f"Activity date must fall between trip dates ({trip['start_date']} to {trip['end_date']})."
                    )
            except ValueError:
                errors["activity_date"] = "Invalid date format (YYYY-MM-DD)."

        act_time = None
        if not time_str:
            errors["activity_time"] = "Activity time is required."
        else:
            try:
                act_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                try:
                    act_time = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
                except ValueError:
                    errors["activity_time"] = "Invalid time format (HH:MM)."

        if not category or category not in ACTIVITY_CATEGORIES:
            errors["category"] = "Please select a valid category."

        if not place:
            errors["place"] = "Place is required."

        act_cost = None
        if not cost_str:
            errors["cost"] = "Estimated cost is required."
        else:
            try:
                act_cost = Decimal(cost_str)
                if act_cost < 0:
                    errors["cost"] = "Activity cost cannot be negative."
            except (InvalidOperation, ValueError):
                errors["cost"] = "Cost must be a valid numeric amount."

        if not errors:
            try:
                cursor.execute(
                    """
                    UPDATE activities
                    SET name = %s, activity_date = %s, activity_time = %s, category = %s, place = %s, cost = %s
                    WHERE id = %s
                    """,
                    (name, act_date, act_time, category, place, act_cost, activity_id),
                )
                db_conn.commit()
                cursor.close()
                flash("Activity updated and budget recalculated!", "success")
                return redirect(url_for("trip_detail", trip_id=trip["id"]))
            except Error as err:
                db_conn.rollback()
                app.logger.error(f"Error editing activity: {err}")
                errors["general"] = "Database error while updating activity."

        cursor.close()

    activity_view = {
        "id": act_row["id"],
        "trip_id": act_row["trip_id"],
        "name": act_row["name"],
    }
    return render_template(
        "activity_form.html",
        is_edit=True,
        trip=trip,
        activity=activity_view,
        errors=errors,
        form_data=form_data,
        categories=ACTIVITY_CATEGORIES,
    )


@app.route("/activities/<int:activity_id>/delete", methods=["POST"])
@login_required
def delete_activity(activity_id: int):
    """Page 6: Remove an activity from itinerary. Auto-recalculates budget."""
    user_id = session["user_id"]

    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT a.trip_id, a.name
            FROM activities a
            JOIN trips t ON a.trip_id = t.id
            WHERE a.id = %s AND t.owner_id = %s
            LIMIT 1
            """,
            (activity_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            cursor.close()
            abort(404)

        trip_id = row["trip_id"]
        act_name = row["name"]
        cursor.execute("DELETE FROM activities WHERE id = %s", (activity_id,))
        db_conn.commit()
        cursor.close()

        flash(f'Activity "{act_name}" removed and budget updated.', "info")
        return redirect(url_for("trip_detail", trip_id=trip_id))
    except Error as err:
        app.logger.error(f"Error deleting activity: {err}")
        flash("Could not delete activity.", "danger")
        return redirect(url_for("my_trips"))


# ---------------------------------------------------------------------------
# CLI Command: Seed Sample Place Suggestions
# ---------------------------------------------------------------------------
SAMPLE_PLACES: List[Dict[str, str]] = [
    {
        "name": "Eiffel Tower",
        "destination": "Paris, France",
        "category": "Sightseeing",
        "description": "Iconic 19th-century iron lattice tower offering breathtaking panoramic views of Paris.",
        "image_url": "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Louvre Museum",
        "destination": "Paris, France",
        "category": "Culture",
        "description": "World famous art museum housing landmark works like the Mona Lisa and Venus de Milo.",
        "image_url": "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Le Marais Bakery Tour",
        "destination": "Paris, France",
        "category": "Food",
        "description": "Taste traditional French croissants, baguettes, and artisan macarons through historic streets.",
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Senso-ji Temple",
        "destination": "Tokyo, Japan",
        "category": "Culture",
        "description": "Tokyo ancient Buddhist temple with vibrant Nakamise shopping street and sacred pagoda.",
        "image_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Tsukiji Outer Market Food Crawl",
        "destination": "Tokyo, Japan",
        "category": "Food",
        "description": "Savor world-class fresh sashimi, tamagoyaki, wagyu skewers, and matcha sweets.",
        "image_url": "https://images.unsplash.com/photo-1540648639573-8c848de23f0a?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Mount Fuji Hiking Tour",
        "destination": "Tokyo, Japan",
        "category": "Adventure",
        "description": "Ascend scenic trails with views across the Five Lakes and breathtaking sunrise vistas.",
        "image_url": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Uluwatu Cliff Temple & Sunset",
        "destination": "Bali, Indonesia",
        "category": "Culture",
        "description": "Cliffside Balinese sea temple perched high above crashing Indian Ocean waves.",
        "image_url": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Tegallalang Rice Terraces",
        "destination": "Bali, Indonesia",
        "category": "Nature",
        "description": "Emerald green stepped rice paddies surrounded by palm trees and jungle swing trails.",
        "image_url": "https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Grand Bazaar Shopping",
        "destination": "Istanbul, Turkey",
        "category": "Shopping",
        "description": "One of the world largest and oldest covered markets with spices, lanterns, and textiles.",
        "image_url": "https://images.unsplash.com/photo-1527838832700-5059252407fa?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Bosphorus Sunset Cruise",
        "destination": "Istanbul, Turkey",
        "category": "Sightseeing",
        "description": "Sail between Europe and Asia past waterfront palaces, fortresses, and skyline minarets.",
        "image_url": "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Colosseum & Roman Forum Tour",
        "destination": "Rome, Italy",
        "category": "Sightseeing",
        "description": "Step into ancient gladiatorial arena history and the vibrant civic heart of classical Rome.",
        "image_url": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=800&q=80",
    },
    {
        "name": "Trastevere Artisan Trattoria Dinner",
        "destination": "Rome, Italy",
        "category": "Food",
        "description": "Authentic handmade cacio e pepe, carbonara, and Italian wine in cobblestone alleyways.",
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=800&q=80",
    },
]


@app.cli.command("seed-db")
def seed_db():
    """CLI command: Seed initial place suggestions into MySQL database."""
    count = 0
    try:
        db_conn = get_db()
        cursor = db_conn.cursor(dictionary=True)
        for item in SAMPLE_PLACES:
            cursor.execute(
                "SELECT id FROM place_suggestions WHERE name = %s AND destination = %s LIMIT 1",
                (item["name"], item["destination"]),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO place_suggestions (name, destination, category, description, image_url)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (item["name"], item["destination"], item["category"], item["description"], item["image_url"]),
                )
                count += 1
        db_conn.commit()
        cursor.close()
        print(f"Database seeded with {count} new place suggestions.")
    except Error as err:
        print(f"Failed to seed database: {err}")


# ---------------------------------------------------------------------------
# Application Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
