# ✈️ Trip Planner Web Application (Modern SQLAlchemy 2.0 ORM)

A full-stack, responsive travel itinerary and budget management web application built with **Flask**, **MySQL**, and modern **Flask-SQLAlchemy 3.x / SQLAlchemy 2.0**.

---

## 🌟 Modern ORM Features

- **SQLAlchemy 2.0 Typed Models**: Uses `DeclarativeBase`, `Mapped[...]`, and `mapped_column(...)`.
- **Relationship Management**: Typed `relationship(...)` between `User`, `Trip`, and `Activity` with `cascade="all, delete-orphan"`.
- **Session Tracking & Unit of Work**: Uses `db.session.add()`, `db.session.get()`, `db.session.delete()`, and `db.session.commit()`.
- **Modern Query Syntax**: Modern SQLAlchemy 2.0 `db.select(...).where(...)` constructs.
- **Robust Connection String**: Uses `sqlalchemy.engine.URL.create(...)` to safely encode database credentials.
- **Specific Login Feedback**: Clearly flags non-existent users vs. wrong passwords.
- **Automatic Budget Recalculation**: Live calculation of total activity costs, remaining/exceeded budget difference, and progress percentage.
- **Date Boundary Enforcement**: Validates that activity dates fall strictly between trip dates and blocks modifying trip dates if existing activities would fall outside the new window.
- **Explore Search & Filter**: Public exploration catalog with combined name search and category filtering.

---

## 📁 Project Structure

```
C:\Flask\Project_ORM/
├── .env.example          # Environment variable template
├── requirements.txt      # Dependencies (Flask, Flask-SQLAlchemy, SQLAlchemy, mysql-connector-python)
├── README.md             # Complete setup and guide
├── schema.sql            # Optional standalone MySQL table script
├── app.py                # Single consolidated application with SQLAlchemy 2.0 ORM
├── static/
│   ├── css/
│   │   └── style.css     # Responsive travel UI design
│   └── js/
│       └── main.js       # Client validation and interactive UI alerts
└── templates/
    ├── base.html         # Navigation bar, alerts, footer
    ├── home.html         # Hero banner, features, and sample destinations
    ├── register.html     # Registration form
    ├── login.html        # Authentication form with specific error alerts
    ├── my_trips.html     # User trips cards & budget statuses
    ├── trip_form.html    # Create & edit trip form
    ├── trip_detail.html  # Trip dashboard & daily timeline
    ├── activity_form.html# Add & edit activity form
    ├── explore.html      # Public places search & filter
    ├── 404.html          # Not found page
    └── 500.html          # Server error page
```

---

## 🚀 How to Run the Application

### 1. Start MySQL Server
Ensure the MySQL Windows Service is active:
```powershell
Start-Service -Name MYSQL80
```

### 2. Configure Environment (`.env`)
In `C:\Flask\Project_ORM`, copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Edit `.env` if your password or database name differs:
```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=trip-planner-orm-adventures-session-secret-key-2026

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=trip_planner_db
```

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Run the Application
```powershell
python app.py
```
*(On first launch, `db.create_all()` will automatically create any missing tables and seed initial destination suggestions).*

### 5. Open in Browser
Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
