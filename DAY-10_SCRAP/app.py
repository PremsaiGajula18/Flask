import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, abort, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure instance directory exists
os.makedirs(app.instance_path, exist_ok=True)

# ==============================================================================
# Database Utilities
# ==============================================================================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS contact_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            company TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    seed_demo_data(db)

def seed_demo_data(db):
    user_count = db.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    if user_count == 0:
        print("[DB] Seeding initial Recruitify demo accounts...")
        demo_pass = generate_password_hash("DemoPass123!")
        db.execute(
            "INSERT INTO users (full_name, username, password_hash) VALUES (?, ?, ?)",
            ("Alex Miller", "demo_user", demo_pass)
        )
        db.execute(
            "INSERT INTO users (full_name, username, password_hash) VALUES (?, ?, ?)",
            ("Lucas Swierad", "lucas_swierad", demo_pass)
        )
        db.commit()
        print("[DB] Demo database successfully seeded!")

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    print('Initialized the database.')

# Auto initialize DB before first request
@app.before_request
def auto_init_db():
    if not hasattr(app, '_db_initialized'):
        try:
            init_db()
            app._db_initialized = True
        except Exception as e:
            print(f"[DB Init Error] {e}")

# ==============================================================================
# Security & CSRF Protection
# ==============================================================================

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(16)
    return session['_csrf_token']

@app.before_request
def csrf_protect():
    if app.config.get('TESTING'):
        return
    if request.method == 'POST':
        token = session.get('_csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or token != form_token:
            flash('Security validation failed: Invalid or expired CSRF token.', 'danger')
            return redirect(request.referrer or url_for('index'))

@app.context_processor
def inject_global_template_vars():
    user = None
    if 'user_id' in session:
        db = get_db()
        user = db.execute(
            "SELECT id, full_name, username FROM users WHERE id = ?",
            (session['user_id'],)
        ).fetchone()
        if not user:
            session.clear()
    return {
        'current_user': user,
        'csrf_token': generate_csrf_token(),
        'current_year': datetime.now().year
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in with your credentials to access the ATS Dashboard.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# Error Handlers
# ==============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', active_page='404'), 404

# ==============================================================================
# Multi-Page Website Routes
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html', active_page='home')

@app.route('/features')
def features():
    return render_template('features.html', active_page='features')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html', active_page='pricing')

@app.route('/about')
def about():
    return render_template('about.html', active_page='about')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        message = request.form.get('message', '').strip()

        if not full_name or not email or not message:
            flash('Please fill out all required contact form fields.', 'danger')
            return redirect(url_for('contact'))

        db = get_db()
        db.execute(
            "INSERT INTO contact_inquiries (full_name, email, company, message) VALUES (?, ?, ?, ?)",
            (full_name, email, company, message)
        )
        db.commit()

        flash('Thank you! Your message has been received. Our sales team will get back to you within 2 hours.', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', active_page='contact')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return redirect(url_for('login'))

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', active_page='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not full_name or not username or not password:
            flash('Please complete all registration fields.', 'warning')
            return redirect(url_for('register'))

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash('That username is already taken. Please pick another one.', 'danger')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (full_name, username, password_hash) VALUES (?, ?, ?)",
            (full_name, username, password_hash)
        )
        db.commit()

        session.clear()
        session['user_id'] = cursor.lastrowid
        session['username'] = username
        flash('Account created successfully! Welcome to your Recruitify trial.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html', active_page='register')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out of Recruitify.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', active_page='dashboard')

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
