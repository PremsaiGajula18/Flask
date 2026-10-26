from flask import Flask, render_template, request, jsonify
import mysql.connector
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

app = Flask(__name__)


# -----------------------------
# MySQL Connection
# -----------------------------
def get_db_connection():

    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    return db


# -----------------------------
# Home Page - GET
# -----------------------------
@app.route("/")
def home():

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "home.html",
        students=students
    )


# -----------------------------
# Add Student - POST
# -----------------------------
@app.route("/add", methods=["POST"])
def add_student():

    # Receive JSON data from JavaScript
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    age = data.get("age")

    # Basic validation
    if not name or not email or not age:
        return jsonify({
            "success": False,
            "message": "All fields are required"
        }), 400

    # Connect to MySQL
    db = get_db_connection()
    cursor = db.cursor()

    # Insert data
    sql = """
        INSERT INTO students (name, email, age)
        VALUES (%s, %s, %s)
    """

    values = (name, email, age)

    cursor.execute(sql, values)

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "success": True,
        "message": "Student added successfully"
    })


# -----------------------------
# Run Flask
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)