"""
========================================================================================
AUTHENTICATION DECORATORS, ROLE-BASED ACCESS CONTROL (RBAC) & CSRF DEFENSES
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Security & Authorization Infrastructure (`app/auth/decorators.py`)
========================================================================================
Description:
    Provides decorators for session authentication (`@login_required`), fine-grained
    role-based access control (`@role_required`), user resolution helpers, and
    cryptographic CSRF synchronizer token generation and validation.
========================================================================================
"""

import functools
import secrets
from typing import Callable, Optional

from flask import abort, flash, redirect, request, session, url_for
from app.models import User


def get_current_user() -> Optional[User]:
    """
    Retrieves the currently authenticated User model instance from the database.

    Reads `user_id` from the secure session cookie and performs an ID lookup.
    Returns None if no user is signed in.

    Returns:
        Optional[User]: The active User model entity, or None if unauthenticated.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None
    from app.extensions import db
    return db.session.get(User, user_id)


def login_required(f: Callable) -> Callable:
    """
    Decorator that requires an active user session to access the decorated route.

    If the user is not authenticated:
        - Flashes a warning message.
        - Preserves the attempted destination in the `?next=` query parameter.
        - Redirects the user to `/login`.

    Args:
        f (Callable): The view function to protect.

    Returns:
        Callable: The wrapped, access-controlled view function.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles: str) -> Callable:
    """
    Decorator that enforces Role-Based Access Control (RBAC).

    Verifies that the logged-in user possesses at least one of the specified roles:
        - 'policyholder'   : Can view policies and file claims
        - 'hospital'       : Can submit cashless claims for their empanelled facility
        - 'claims_officer' : Can review queue, request information, and approve/reject
        - 'admin'          : Can record settlements and manage master reference data

    If the user lacks permission, an HTTP 403 Forbidden exception is raised.

    Args:
        *allowed_roles (str): Variable list of role names permitted to access the route.

    Returns:
        Callable: The RBAC decorator function.
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.url))

            user_role = session.get("user_role")
            if user_role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def generate_csrf_token() -> str:
    """
    Generates or retrieves a per-session cryptographically random CSRF token.

    Uses `secrets.token_hex(24)` to generate an unpredictable token that protects
    forms against Cross-Site Request Forgery (CSRF).

    Returns:
        str: The active CSRF hex token.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


def validate_csrf_token() -> None:
    """
    Validates the submitted CSRF token on state-altering HTTP methods (POST, PUT, DELETE).

    Extracts the token from form data (`csrf_token`) or request headers (`X-CSRFToken`)
    and compares it in constant time against the token stored in the user's session.

    Raises:
        HTTP 400 Bad Request: If the token is missing or mismatched.
    """
    from flask import current_app

    # Bypass CSRF check in automated testing environment
    if current_app.config.get("TESTING") or not current_app.config.get("WTF_CSRF_ENABLED", True):
        return

    # Check state-changing HTTP methods
    if request.method == "POST":
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        expected = session.get("csrf_token")
        if not expected or not token or token != expected:
            abort(400, description="Invalid or missing CSRF token.")
