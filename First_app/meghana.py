from flask import Flask

app = Flask(__name__)
#Create a Flask web application Object
@app.route("/")
def home():
    return "Welcome to Student Management System"

# Student Information Route
#Decorator = a function that takes another function and adds behavior to it
@app.route("/students")
#A route is a rule that tells Flask: "When the user visits this URL, call this function."
def student_information():
    return """
   <h1>Student Information</h1>
    <ul>
        <li><b>Batch Name:</b> MITRAz BSc Computer Science</li>
        <li><b>Number of Students:</b> 21</li>
        <li><b>Technology:</b> Python, Flask, MySQL</li>
        <li><b>Current Module:</b> Flask Web Development</li>
        <li><b>Training Mode:</b> Offline</li>
    </ul>
    """
@app.route("/student/<name>")
def student(name):
    return f"Student Name: {name}"


@app.route("/prem")
def carrer():
     return name

if __name__ == "__main__":
   #Debug mode helps you find and fix errors while developing your Flask application.
        app.run(debug=True)

    # Debug mode OFF (production)
         