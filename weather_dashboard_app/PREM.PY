
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)

# Required for Flask's session-based flash messages
app.config["SECRET_KEY"] = "replace-with-a-secure-secret"

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Flash Messages</title>
</head>
<body>
    <h2>Student Registration</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <p><strong>{{ category }}:</strong> {{ message }}</p>
        {% endfor %}
    {% endwith %}

    <form method="POST" action="/register">
        <input type="text" name="username" placeholder="Enter username">
        <button type="submit">Register</button>
    </form>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()

    if not username:
        flash("Username is required!", "danger")
    else:
        flash("Registration successful!", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
