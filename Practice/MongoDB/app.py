from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

app = Flask(__name__)


# --------------------------------
# MongoDB Connection
# --------------------------------

mongo_client = MongoClient(os.getenv("MONGO_URI"))

db = mongo_client[os.getenv("MONGO_DB")]

students_collection = db[os.getenv("MONGO_COLLECTION")]


# --------------------------------
# Home Page - GET
# --------------------------------

@app.route("/")
def home():

    # Get all students from MongoDB
    students = list(
        students_collection.find()
    )

    return render_template(
        "home.html",
        students=students
    )


# --------------------------------
# Add Student - POST
# --------------------------------

@app.route("/add", methods=["POST"])
def add_student():

    # Receive JSON from JavaScript
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    age = data.get("age")


    # Validation

    if not name or not email or not age:

        return jsonify({
            "success": False,
            "message": "All fields are required"
        }), 400


    # Create MongoDB document

    student = {
        "name": name,
        "email": email,
        "age": int(age)
    }


    # Insert into MongoDB

    result = students_collection.insert_one(student)


    return jsonify({
        "success": True,
        "message": "Student added successfully",
        "id": str(result.inserted_id)
    })


# --------------------------------
# Run Flask
# --------------------------------

if __name__ == "__main__":
    app.run(debug=True)