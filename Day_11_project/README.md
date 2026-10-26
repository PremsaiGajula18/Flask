# ✈️ Trip Planner Web Application

A full-stack travel itinerary and budgeting web application built with **Flask**, **MySQL**, and modern **HTML5/CSS3/JavaScript**, consolidated into a **single `app.py`** application architecture identical to `DAY-10_PROJECT`.

---

## 📁 Consolidated Project Structure

```
C:\Flask\Day_11_project/
├── .env.example          # Environment variable template
├── requirements.txt      # Clean dependencies (Flask, mysql-connector-python, Werkzeug)
├── README.md             # Setup and usage guide
├── schema.sql            # MySQL schema creation & seed script
├── app.py                # Single consolidated application (database, auth, CSRF, routes, logic)
├── static/
│   ├── css/
│   │   └── style.css     # Responsive design and modern styles
│   └── js/
│       └── main.js       # Client-side validation and interactive feedback
└── templates/
    ├── base.html         # Navbar, footer, and flash messages
    ├── home.html         # Landing hero, features, and sample destinations
    ├── register.html     # User registration form
    ├── login.html        # Authentication form
    ├── my_trips.html     # User's trips list and summary cards
    ├── trip_form.html    # Create and edit trip form
    ├── trip_detail.html  # Trip dashboard and daily itinerary timeline
    ├── activity_form.html# Add and edit activity form
    ├── explore.html      # Public places exploration catalog
    ├── 404.html          # Not found error page
    └── 500.html          # Internal server error page
```

---

## 🚀 How to Run the Application

### 1. Start MySQL Server
Ensure MySQL server is running (e.g. via Windows Services or PowerShell):
```powershell
Start-Service -Name MYSQL80
```

### 2. Initialize the Database
Open PowerShell in `C:\Flask\Day_11_project` and run:
```powershell
mysql -u root -p < schema.sql
```
*(Enter your MySQL password when prompted)*

### 3. Configure `.env`
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your database credentials match:
```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=trip-planner-adventures-session-secret-key-2026

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=trip_planner_db
```

### 4. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 5. Run the Server
```powershell
python app.py
```

### 6. Open in Browser
Open your browser and visit:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
