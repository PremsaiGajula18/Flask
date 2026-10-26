from flask import redirect
from flask import Flask, request, url_for

app = Flask(__name__)
#Create a Flask web application Object
students = [] 

#Decorator = a function that takes another function and adds behavior to it
@app.route("/")
def home():
    return f"""
    <h1>Student List</h1>
    
    <form action="{url_for('add_student')}" method="POST">
        <input type="text" name="name" placeholder="Enter student name">
        <button type="submit">Add Student</button>
    </form>

    <h2>Students</h2>
    <ul>
        {"".join(f"<li>{student}</li>" for student in students)}
    </ul>
    """


@app.route("/add", methods=["POST"])
def add_student():

    name = request.form.get("name")

    students.append(name)

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)