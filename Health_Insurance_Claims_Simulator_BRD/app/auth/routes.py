"""
========================================================================================
AUTHENTICATION & USER REGISTRATION BLUEPRINT CONTROLLER
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Authentication Controller (`app/auth/routes.py`)
========================================================================================
Description:
    Manages user sign-in, self-registration with dynamic role selection (Policyholder,
    Hospital Desk, Claims Officer, System Admin), password verification using Scrypt,
    session initialization, and secure logout.
========================================================================================
"""

import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.decorators import login_required
from app.extensions import db
from app.models import User, Hospital, Policy, Member, Plan

# Authentication Blueprint mounted without prefix (e.g. /login, /register, /logout)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    User Sign-In Route.

    GET:
        Renders the clean username/password sign-in form. If the user is already
        authenticated, redirects them directly to the main dashboard.

    POST:
        1. Retrieves submitted credentials ('username' and 'password').
        2. Queries the User model for matching username.
        3. Verifies password hash using Werkzeug's Scrypt algorithm.
        4. On success, initializes session values (user_id, username, display_name,
           user_role, hospital_id) and redirects to destination URL (?next=) or dashboard.
        5. On failure, flashes an error alert and re-renders the login screen.
    """
    if "user_id" in session:
        return redirect(url_for("claims.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        # Step 1: Check if the username exists in the system
        if not user:
            flash(f"Username '{username}' is wrong. User does not exist.", "danger")
            return render_template("auth/login.html", entered_username=username)

        # Step 2: Username exists; now check if password matches
        if not check_password_hash(user.password_hash, password):
            flash("Password is wrong. Please check your password and try again.", "danger")
            return render_template("auth/login.html", entered_username=username)

        # Step 3: Both username and password are correct -> Log in
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session["display_name"] = user.display_name
        session["user_role"] = user.role
        session["hospital_id"] = user.hospital_id

        flash(f"Welcome back, {user.display_name} ({user.role.replace('_', ' ').title()})!", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("claims.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Role-Based User Self-Registration Route.

    GET:
        Renders the multi-role registration form with live dynamic field toggles:
        - Hospital selection for Hospital Desk accounts
        - Plan subscription selection for Policyholder accounts

    POST:
        1. Validates required fields, password length (minimum 6 chars), and confirmation match.
        2. Ensures the chosen username is unique across the database.
        3. For 'hospital' role, verifies that an empanelled hospital ID is selected.
        4. Creates new User record with Scrypt password hashing.
        5. For 'policyholder' role, automatically issues an active 1-year starter Policy
           and primary self-Member record so claims can be submitted immediately.
        6. Commits changes to MySQL and redirects user to `/login`.
    """
    if "user_id" in session:
        return redirect(url_for("claims.dashboard"))

    hospitals = Hospital.query.filter_by(network_status=True).all()
    plans = Plan.query.all()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "policyholder").strip()
        hospital_id = request.form.get("hospital_id")
        plan_id = request.form.get("plan_id")

        # Step 1: Input presence and basic format validation
        if not username or not display_name or not password:
            flash("All required fields must be filled out.", "danger")
            return render_template("auth/register.html", hospitals=hospitals, plans=plans)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return render_template("auth/register.html", hospitals=hospitals, plans=plans)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html", hospitals=hospitals, plans=plans)

        # Step 2: Uniqueness check on username
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f"The username '{username}' is already taken. Please choose another one.", "warning")
            return render_template("auth/register.html", hospitals=hospitals, plans=plans)

        # Step 3: Hospital Desk constraint check
        assigned_hospital_id = None
        if role == "hospital":
            if not hospital_id:
                flash("Please select an empanelled hospital for hospital desk staff.", "danger")
                return render_template("auth/register.html", hospitals=hospitals, plans=plans)
            assigned_hospital_id = int(hospital_id)

        # Step 4: Create User record with secure Scrypt hash
        new_user = User(
            username=username,
            display_name=display_name,
            role=role,
            hospital_id=assigned_hospital_id,
            password_hash=generate_password_hash(password, method="scrypt")
        )
        db.session.add(new_user)
        db.session.flush()

        # Step 5: Auto-provision starter policy and member for policyholders
        if role == "policyholder":
            chosen_plan = Plan.query.get(int(plan_id)) if plan_id else Plan.query.first()
            today = datetime.date.today()
            starter_policy = Policy(
                holder_user_id=new_user.id,
                plan_id=chosen_plan.id if chosen_plan else 1,
                start_date=today - datetime.timedelta(days=30),
                end_date=today + datetime.timedelta(days=335),
                status="active"
            )
            db.session.add(starter_policy)
            db.session.flush()

            self_member = Member(
                policy_id=starter_policy.id,
                display_name=display_name,
                relationship="self"
            )
            db.session.add(self_member)

        db.session.commit()
        flash(f"Account for '{display_name}' ({role.replace('_', ' ').title()}) created successfully! Please sign in below.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", hospitals=hospitals, plans=plans)


@auth_bp.route("/logout")
def logout():
    """
    Session Termination Route.

    Clears all session variables (user_id, roles, tokens) to completely sign out
    the user and redirects them to the login screen with a confirmation alert.
    """
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))
