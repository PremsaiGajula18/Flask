from flask import Flask, request, render_template_string

app = Flask(__name__)

stories = []

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        story = request.form.get("story")
        stories.append(story)

    return render_template_string("""
        <form method="POST">
            <input name="story" placeholder="Enter a story">
            <button type="submit">Submit</button>
        </form>

        {% for story in stories %}
            <p>{{ story }}</p>
        {% endfor %}
    """, stories=stories)

if __name__ == "__main__":
    app.run(debug=True)