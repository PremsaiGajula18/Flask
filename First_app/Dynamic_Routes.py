from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to Student Portal"


@app.route("/student/<name>")
def student(name):
    return f"Hello {name}"


@app.route("/course/<course_name>")
def course(course_name):
    return f"You selected {course_name} course"


if __name__ == "__main__":
    app.run(debug=True)