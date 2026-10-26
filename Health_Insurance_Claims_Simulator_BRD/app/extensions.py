"""
========================================================================================
DATABASE EXTENSION INSTANTIATION (UNBOUND EXTENSION PATTERN)
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Database Extensions Layer (`app/extensions.py`)
========================================================================================
Description:
    Instantiates the SQLAlchemy ORM instance in an 'unbound' state without attaching it
    to any specific Flask application. This prevents circular import dependencies
    between models and the application factory.
========================================================================================
"""

from flask_sqlalchemy import SQLAlchemy

# Unbound SQLAlchemy database handler.
# Bound to the app during startup inside `app/__init__.py: create_app() -> db.init_app(app)`.
db = SQLAlchemy()
