from flask import Flask

# Task 1: Create Flask application
app = Flask(__name__)


# Task 2: Home Route
@app.route("/")
def home():
    return """
    <h1>Welcome to MITRAz Student Help Portal</h1>

    <h2>Available Services:</h2>

    <ol>
        <li>Student Information</li>
        <li>Course Information</li>
        <li>Faculty Information</li>
        <li>Batch Information</li>
        <li>Contact Information</li>
    </ol>
    """


# Student Information Route
@app.route("/student")
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

@app.route("/courses")
def Courses():
    return """
          <h1>liSt of Courses</h1>
          <ol>
          <li>Python</li>
          <li>My sql</li>
          <li>mongoDb</li>
          <li>HTML</li>
          <li>CSS</li>
          <li>Java Script</li>
          </ol>
    """

# Task 5: Faculty Information
@app.route("/faculty")
def faculty_information():
    return """
    <h1>Faculty Information</h1>

    <h2>Faculty / Trainers</h2>

    <ol>
        <li>
            <b>Name:</b> Sri Lakshmi Mam<br>
            <b>Subject:</b>Full Stack
        </li>
        <br>

        <li>
            <b>Name:</b> Sreeni Sir <br>
            <b>Subject:</b> Full Stack, Zoho Crm 
        </li>
        <br>

        <li>
            <b>Name:</b> Lahari Mam<br>
            <b>Subject:</b> Full Stack, Zoho Crm 
        </li>
    </ol>
    """
# Task 6: Batch Information
@app.route("/batch")
def batch_information():
    return """
    <h1>Batch Information</h1>

    <ul>
        <li><b>Batch Name:</b>IT_7</li>
        <li><b>Start Date:</b> 01 Jan 2026</li>
        <li><b>Duration:</b> 6 Months</li>
        <li><b>Number of Students:</b> 21</li>
        <li><b>Current Technology:</b> Python & Flask</li>
    </ul>
    """


# Task 7: Contact Information
@app.route("/contact")
def contact_information():
    return n

# Task 8: Dynamic Student Route
@app.route("/student/<name>")
def dynamic_student(name):
    return f"""
    <h1>MITRAz Student Portal</h1>

    <h2>Welcome {name.title()}!</h2>

    <p>You are viewing the MITRAz Student Portal.</p>
    """


# Task 9: Dynamic Course Route
@app.route("/course/<course_name>")
def dynamic_course(course_name):
    return f"""
    <h1>MITRAz Course Information</h1>

    <h2>Course: {course_name.upper()}</h2>

    <p>You are viewing information about the {course_name.title()} course.</p>
    """



# Run Flask application in debug mode
if __name__ == "__main__":
    app.run(debug=True)