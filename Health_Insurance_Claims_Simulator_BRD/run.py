"""
========================================================================================
APPLICATION ENTRYPOINT & WSGI LOCAL SERVER RUNNER
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Framework   : Flask 3.x (WSGI Application Factory Pattern)
Database    : MySQL 8.0 Server via PyMySQL DBAPI
Architecture: Layered Clean Architecture (Blueprints, Domain Services, SQLAlchemy ORM)
========================================================================================
Description:
    This module serves as the primary executable entrypoint for the development server.
    It instantiates the Flask application using the Application Factory `create_app()`
    defined in `app/__init__.py`, reads runtime configuration from the OS environment,
    and binds the built-in Werkzeug development server to localhost.

Execution:
    Run directly using Python:
        $ python run.py
    Or via the Flask CLI:
        $ flask run
========================================================================================
"""

import os
from app import create_app

# --------------------------------------------------------------------------------------
# Application Instantiation (Factory Pattern)
# --------------------------------------------------------------------------------------
# Instantiates a fresh Flask WSGI instance configured exclusively for MySQL 8.0.
# All database connections, Blueprints, and CSRF hooks are registered during this call.
app = create_app()

if __name__ == "__main__":
    # Retrieve port and debugging flags from environment, with safe defaults
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")

    # Display startup banner with active environment details
    print("=" * 65)
    print("  HEALTH INSURANCE CLAIMS PROCESSING SIMULATOR (BRD SYSTEM)")
    print("=" * 65)
    print(f"  * Runtime Engine : Python (Flask WSGI Application)")
    print(f"  * Active Database: MySQL 8.0 (health_claims_simulator)")
    print(f"  * Local Host     : 127.0.0.1")
    print(f"  * Server Port    : {port}")
    print(f"  * Access URL     : http://127.0.0.1:{port}")
    print(f"  * Debug Mode     : {'Enabled (Auto-reload active)' if debug else 'Disabled (Production)'}")
    print("=" * 65)

    # Launch local WSGI development server
    app.run(host="127.0.0.1", port=port, debug=debug)
