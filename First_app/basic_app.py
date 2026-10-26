from flask import Flask

app = Flask(__name__)
#Create a Flask web application Object
@app.route("/")
#Decorator = a function that takes another function and adds behavior to it
#A route is a rule that tells Flask: "When the user visits this URL, call this function."
def home():
    return "Hello, Flask!"


if __name__ == "__main__":
     app.run(debug=True)