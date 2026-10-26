from flask import Flask, render_template, request

app = Flask(__name__)

# Temporary list to store students
students = []


# --------------------------------
# HOME PAGE
# --------------------------------

@app.route("/")
def home():

    return render_template(
        "home.html",
        students=students
    )


# --------------------------------
# ADD STUDENT - POST
# --------------------------------

@app.route("/add", methods=["POST"])
def add_student():

    # Get data from form
    name = request.form.get("name")

    # Save student
    students.append(name)

    # ❌ PROBLEM:
    # Directly render the template after POST

    return render_template(
        "success.html",
        name=name
    )


# --------------------------------
# RUN APPLICATION
# --------------------------------

if __name__ == "__main__":
    app.run(debug=True)