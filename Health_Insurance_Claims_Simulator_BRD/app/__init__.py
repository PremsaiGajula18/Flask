"""
========================================================================================
APPLICATION FACTORY, EXTENSIONS INITIALIZATION & MIDDLEWARE
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Application Core Initialization (`app/__init__.py`)
Pattern     : Flask Application Factory Pattern
========================================================================================
Description:
    Implements `create_app()` to initialize database extensions, register modular Blueprints,
    attach global CSRF protection hooks, install Indian Rupee currency formatters, and
    configure user-friendly HTTP error handlers (403, 404, 500).
========================================================================================
"""

import os
from decimal import Decimal
from typing import Optional

from flask import Flask, render_template, session

from app.auth.decorators import generate_csrf_token, validate_csrf_token
from config import Config
from app.extensions import db


class CurrentUserProxy:
    """
    Session Proxy providing ergonomic `current_user` property access in Jinja2 templates.

    Allows templates to query authentication state and role permissions cleanly:
        {% if current_user.is_authenticated %}
            <span>Welcome, {{ current_user.display_name }}</span>
        {% endif %}
    """

    @property
    def is_authenticated(self) -> bool:
        """Returns True if an active user session exists, False otherwise."""
        return "user_id" in session

    @property
    def id(self) -> Optional[int]:
        """Returns the primary key ID of the logged-in user."""
        return session.get("user_id")

    @property
    def username(self) -> Optional[str]:
        """Returns the unique username of the logged-in user."""
        return session.get("username")

    @property
    def display_name(self) -> Optional[str]:
        """Returns the human-friendly display name of the user."""
        return session.get("display_name")

    @property
    def role(self) -> Optional[str]:
        """Returns the user's role: 'policyholder', 'hospital', 'claims_officer', or 'admin'."""
        return session.get("user_role")

    @property
    def hospital_id(self) -> Optional[int]:
        """Returns the linked hospital foreign key ID for hospital desk users, or None."""
        return session.get("hospital_id")


def format_inr(value) -> str:
    """
    Formats a numeric value or Decimal into standard Indian Rupee currency formatting.

    Args:
        value (int | float | Decimal | str | None): Monetary figure to format.

    Returns:
        str: Formatted string (e.g. '₹1,50,000.00' or '₹0.00').
    """
    if value is None:
        return "₹0.00"
    try:
        val = Decimal(str(value))
        return f"₹{val:,.2f}"
    except Exception:
        return f"₹{value}"


def create_app(config_class=Config) -> Flask:
    """
    Flask Application Factory.

    Instantiates and configures the Flask application, binds SQLAlchemy ORM,
    mounts feature Blueprints, establishes CSRF security middleware, and registers
    global template filters and custom HTTP error handlers.

    Args:
        config_class: Configuration object or class containing settings (default Config).

    Returns:
        Flask: The fully configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ----------------------------------------------------------------------------------
    # Initialize Database Extensions
    # ----------------------------------------------------------------------------------
    db.init_app(app)

    # ----------------------------------------------------------------------------------
    # Register Feature Blueprints
    # ----------------------------------------------------------------------------------
    from app.auth.routes import auth_bp
    from app.claims.routes import claims_bp
    from app.officer.routes import officer_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp)       # Authentication & Registration routes
    app.register_blueprint(claims_bp)     # Policyholder claims & policy dashboards
    app.register_blueprint(officer_bp)    # Claims Officer adjudication review queue
    app.register_blueprint(admin_bp)      # Admin master reference data & settlements

    # ----------------------------------------------------------------------------------
    # Security Middleware: Synchronizer Token CSRF Validation
    # ----------------------------------------------------------------------------------
    @app.before_request
    def check_csrf():
        """
        Intercepts all incoming HTTP requests before reaching view functions.
        Validates the submitted CSRF token on state-altering HTTP methods (POST, PUT, DELETE).
        """
        validate_csrf_token()

    # ----------------------------------------------------------------------------------
    # Global Template Context Processors & Filters
    # ----------------------------------------------------------------------------------
    @app.context_processor
    def inject_context():
        """
        Injects global variables into all Jinja2 templates without passing them manually:
        - current_user: CurrentUserProxy instance for auth status & roles
        - csrf_token: Cryptographically generated token for form protection
        - format_inr: Currency formatting utility function
        - db_engine_name: Indicator string displayed in UI footer
        """
        return {
            "current_user": CurrentUserProxy(),
            "csrf_token": generate_csrf_token(),
            "format_inr": format_inr,
            "db_engine_name": "MySQL 8.0 (health_claims_simulator)",
        }

    # Register the INR currency filter for Jinja syntax: {{ amount | format_inr }}
    app.jinja_env.filters["format_inr"] = format_inr

    # ----------------------------------------------------------------------------------
    # User-Friendly Custom Error Handlers
    # ----------------------------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden_error(e):
        """Renders custom 403 Forbidden page when access is denied."""
        return render_template("shared/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(e):
        """Renders custom 404 Not Found page for non-existent routes/records."""
        return render_template("shared/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        """
        Renders custom 500 Internal Server Error page and rolls back uncommitted
        database transactions to prevent corrupted database state.
        """
        db.session.rollback()
        return render_template("shared/500.html"), 500

    return app
