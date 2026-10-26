from flask import Flask

app = Flask(__name__)
#Create a Flask web application Object

@app.route("/")
def home():
    return "Welcome to Flask!"


@app.route("/student")
def student():
    return prem


@app.route("/error")
def error():
    name = undefined_variable
    return name

'''debug=True
    ↓
Flask Debug Mode ON
    ↓
1. Shows detailed errors
2. Shows traceback
3. Automatically reloads when code changes'''


if __name__ == "__main__":
    app.run(debug=True)