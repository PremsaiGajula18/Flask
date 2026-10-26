"""
========================================================================================
CENTRAL CONFIGURATION & ENVIRONMENT MANAGEMENT
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Application Configuration Layer
Database    : MySQL 8.0 Server
========================================================================================
Description:
    Loads environment variables from `.env` and constructs the database connection URI
    using SQLAlchemy's URL.create() utility. This guarantees safe escaping of complex
    special characters (such as '@', '#', '$') in database credentials.
========================================================================================
"""

import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Load environment key-value pairs from .env into os.environ
load_dotenv()


class Config:
    """
    Centralized configuration class for the Flask application.

    Attributes:
        SECRET_KEY (str): Cryptographic secret key used for signing session cookies
            and synchronizer CSRF tokens.
        DB_USER (str): MySQL database username.
        DB_PASSWORD (str): MySQL database password.
        DB_HOST (str): Host address of MySQL server (default 127.0.0.1).
        DB_PORT (str): Port of MySQL server (default 3306).
        DB_NAME (str): Name of the relational database schema.
        SQLALCHEMY_DATABASE_URI (URL | str): Formatted PyMySQL connection string.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Disables SQLAlchemy event signals to conserve memory.
        SQLALCHEMY_ENGINE_OPTIONS (dict): Connection pool parameters (pre-ping and recycling).
    """

    # Secret key for signing cookies and CSRF tokens
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-health-claims-sim-2026")

    # MySQL connection credentials (read from environment or default local dev setup)
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "premsai444@123")
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "health_claims_simulator")

    # Build the MySQL SQLAlchemy connection URL using URL.create.
    # This prevents parser errors when passwords contain '@', ':', or '#' symbols.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        URL.create(
            "mysql+pymysql",
            username=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            query={"charset": "utf8mb4"},
        ),
    )

    # Disable event signal overhead
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Production connection pool management:
    # - pool_recycle: Recycles connections before MySQL wait_timeout (avoids 'MySQL server has gone away')
    # - pool_pre_ping: Tests socket liveness before checkout to prevent dead connection crashes
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }
