
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, session, g, redirect, Response, abort, url_for
from datetime import datetime
import re

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@34.75.94.195/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@34.75.94.195/proj1part2"
#
DATABASEURI = "postgresql://krw2146:618771@34.74.171.121/proj1part2"

#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)
#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#

# The string needs to be wrapped around text()

# To make the queries run, we need to add this commit line


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: https://flask.palletsprojects.com/en/2.0.x/quickstart/?highlight=routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#

@app.route('/filmmaker/')
def filmmaker():
    # Your filmmaker route logic here
    return render_template('filmmaker.html')


@app.route('/student/', methods=['GET'])
def student():
    print(request.args)
    # Check if the form has been submitted
    if 'studentID' in request.args:
        student_id = request.args.get('studentID', '').lower()
        student_info = fetch_student_info(student_id)
        school_info = fetch_school_info(student_id)
        roles_info = fetch_roles_info(student_id)

        if student_info:
            return render_template('student.html', student_info=student_info, school_info=school_info, roles_info=roles_info)
        else:
            return render_template('student.html', student_not_found=True)

    # If the form has not been submitted, render the empty student.html
    return render_template('student.html', student_info = None)

def fetch_student_info(student_id):
    try:
        cursor = g.conn.execute(text("SELECT * FROM student WHERE studentID = :id"), {'id':student_id})
        student_info = cursor.fetchone()
        return student_info
    finally:
        cursor.close()
def fetch_school_info(student_id):
    print("in fetch school")
    try:
        query = """
            SELECT School.SchoolID, School.Name, School.Location, School.Description, Attends.Since
            FROM School
            JOIN Attends ON School.SchoolID = Attends.SchoolID
            WHERE Attends.StudentID = :id
        """
        cursor = g.conn.execute(text(query), {'id':student_id})
        school_info = cursor.fetchone()
        return school_info
    finally:
        cursor.close()
def fetch_roles_info(student_id):
    try:
        query = """
            SELECT Role.RoleID, Role.Description, Role.Level, Role.Status, Role.Begin, Role.Finish,
                   Film.Title
            FROM Part_Of
            JOIN Role ON Part_Of.RoleID = Role.RoleID
            JOIN Needs ON Role.RoleID = Needs.RoleID
            JOIN Film ON Needs.FilmID = Film.FilmID
            WHERE Part_Of.StudentID = :id
        """
        cursor = g.conn.execute(text(query), {'id':student_id})
        roles_info = cursor.fetchall()
        return roles_info
    finally:
        cursor.close()

@app.route('/register', methods=['POST'])
def register_student():
    try:
        studentID = request.form.get('studentID')
        name = request.form.get('name')
        age = int(request.form.get('age'))
        gender = request.form.get('gender')
        status = int(request.form.get('status'))
        gpa = float(request.form.get('gpa'))

        schoolName = request.form.get('schoolName')
        sinceDate = datetime.strptime(request.form.get('sinceDate'), '%Y-%m-%d')

        # Check if the studentID already exists
        if student_id_exists(studentID):
            error_message = "Error: Student ID already in use. Please choose a different ID."
            return render_template('student.html', error_message=error_message)

        # Insert the new student into the database
        g.conn.execute(
            text("INSERT INTO student (StudentID, Name, Age, Gender, Status, GPA) VALUES (:studentID, :name, :age, :gender, :status, :gpa)"),
            studentID=studentID, name=name, age=age, gender=gender, status=status, gpa=gpa
        )

        # Insert school information into the Attends table
        g.conn.execute(
            text("INSERT INTO Attends (StudentID, SchoolID, Since) VALUES (:studentID, (SELECT SchoolID FROM School WHERE Name = :schoolName), :sinceDate)"),
            studentID=studentID, schoolName=schoolName, sinceDate=sinceDate
        )

        # Redirect to the student view page with the newly registered studentID
        new_student_id = g.conn.execute(text("SELECT MAX(studentID) FROM student")).scalar()
        return redirect(f'/student/?studentID={new_student_id}')

    except Exception as e:
        # Handle any other exceptions that may occur during registration
        error_message = f"An error occurred during registration: {str(e)}"
        return render_template('student.html', error_message=error_message)
    
def student_id_exists(student_id):
    try:
        query = text("SELECT EXISTS(SELECT 1 FROM student WHERE studentID = :id)")
        result = g.conn.execute(query, id=student_id).scalar()
        return result
    except Exception as e:
        error_message = f"Error checking student ID existence: {str(e)}"
        return False

@app.route('/roles')
def roles():
    selected_roles = None

    if request.method == 'GET':
        if request.args.get('action') == 'fetch_all_roles':
            selected_roles = fetch_all_roles()
        elif request.args.get('action') == 'fetch_actor_roles':
            selected_roles = fetch_actor_roles()
        elif request.args.get('action') == 'fetch_producer_roles':
            selected_roles = fetch_producer_roles()
        elif request.args.get('action') == 'fetch_director_roles':
            selected_roles = fetch_director_roles()
        elif request.args.get('action') == 'fetch_crew_roles':
            selected_roles = fetch_crew_roles()

    return render_template('roles.html', roles_available=selected_roles)
   

def fetch_all_roles():
    try:
        query = """
            SELECT A.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title
            FROM Role R      
        """
        cursor = g.conn.execute(text(query), {'id':student_id})
        roles_info = cursor.fetchall()
        return roles_info
    finally:
        cursor.close()

def fetch_actor_roles():
    try:
        query = """
            SELECT A.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title
            FROM Role R
            JOIN Actor A ON R.RoleID = A.RoleID
            JOIN Film F ON R.FilmID = F.FilmID
        """
        cursor = g.conn.execute(text(query))
        roles_info = cursor.fetchall()
        return roles_info
    finally:
        cursor.close()

def fetch_actor_roles():
    try:
        query = """
            SELECT P.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title
            FROM Role R
            JOIN Producer P ON R.RoleID = P.RoleID
            JOIN Film F ON R.FilmID = F.FilmID
        """
        cursor = g.conn.execute(text(query))
        roles_info = cursor.fetchall()
        return roles_info
    finally:
        cursor.close()

def fetch_actor_roles():
    try:
        query = """
            SELECT D.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title
            FROM Role R
            JOIN Director D ON R.RoleID = D.RoleID
            JOIN Film F ON R.FilmID = F.FilmID
        """
        cursor = g.conn.execute(text(query))
        roles_info = cursor.fetchall()
        return roles_info
    finally:
        cursor.close()

def fetch_actor_roles():
    try:
        query = """
            SELECT C.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title
            FROM Role R
            JOIN Crew C ON R.RoleID = C.RoleID
            JOIN Film F ON R.FilmID = F.FilmID
        """
        cursor = g.conn.execute(text(query))
        roles_info = cursor.fetchall()
        return roles_info
    finally:
        cursor.close()

@app.route('/school', methods=['GET'])
def school():
    school_id = request.args.get('schoolID')

    # Get school information
    school_info = fetch_school_info2(school_id)
    students_info = fetch_students_attending_school(school_id)
    films_info = fetch_films_by_school(school_id)

    if school_info:
        return render_template('school.html', school_info=school_info, students_info=students_info, films_info=films_info, school_not_found=False)
    else:
        return render_template('school.html', school_info=None, school_not_found=True)

def fetch_school_info2(school_id):
    try:
        query = """
            SELECT SchoolID, Name, Location, Description
            FROM School
            WHERE SchoolID = :id
        """
        cursor = g.conn.execute(text(query), id=school_id)
        school_info = cursor.fetchone()
        return school_info
    finally:
        cursor.close()

def fetch_students_attending_school(school_id):
    try:
        query = """
            SELECT Student.StudentID, Student.Name, Student.Age, Student.Gender, Student.Status, Student.GPA
            FROM Student
            JOIN Attends ON Student.StudentID = Attends.StudentID
            WHERE Attends.SchoolID = :id
        """
        cursor = g.conn.execute(text(query), id=school_id)
        students_info = cursor.fetchall()
        return students_info
    finally:
        cursor.close()

def fetch_films_by_school(school_id):
    try:
        query = """
            SELECT Film.FilmID, Film.Title, Film.Year, Film.Genre, Film.Description, Film.Stage_of_production, Film.Budget
            FROM Film
            WHERE Film.SchoolID = :id
            ORDER BY Film.Year DESC
        """
        cursor = g.conn.execute(text(query), id=school_id)
        films_info = cursor.fetchall()
        return films_info
    finally:
        cursor.close()
@app.route('/register_school', methods=['POST'])
def register_school():
    try:
        school_id = request.form.get('schoolID')
        name = request.form.get('name')
        location = request.form.get('location')
        description = request.form.get('description')

        # Validate school_id format
        if not re.match(r'^1\d{7}$', school_id):
            error_message = "Error: School ID must be an 8-digit number starting with 1."
            return render_template('school.html', error_message=error_message, school_info=None, school_not_found=True)

        # Check if the schoolID already exists
        if school_id_exists(school_id):
            error_message = "Error: School ID already in use. Please choose a different ID."
            return render_template('school.html', error_message=error_message, school_info=None, school_not_found=True)

        # Insert the new school into the database
        g.conn.execute(
            text("INSERT INTO School (SchoolID, Name, Location, Description) VALUES (:schoolID, :name, :location, :description)"),
            schoolID=school_id, name=name, location=location, description=description
        )

        # Redirect to the school view page with the newly registered schoolID
        return redirect(f'/school/?schoolID={school_id}')

    except Exception as e:
        # Handle any other exceptions that may occur during registration
        error_message = f"An error occurred during registration: {str(e)}"
        return render_template('school.html', error_message=error_message, school_info=None, school_not_found=True)
    
def school_id_exists(school_id):
    try:
        query = text("SELECT EXISTS(SELECT 1 FROM School WHERE SchoolID = :schoolID)")
        result = g.conn.execute(query, schoolID=school_id).scalar()
        return result
    except Exception as e:
        error_message = f"Error checking school ID existence: {str(e)}"
        return False

@app.route('/film', methods=['GET'])
def film():
    film_id = request.args.get('filmID')

    # Fetch all schools separately
    all_schools = fetch_all_schools()

    # Get film information
    film_info = fetch_film_info(film_id)
    school_info = fetch_school_info_by_film(film_id)

    if film_info:
        return render_template('filmmaker.html', film_info=film_info, school_info=school_info, all_schools=all_schools, film_not_found=False)
    else:
        return render_template('filmmaker.html', film_info=None, school_info=None, film_not_found=True, all_schools=all_schools)
    
def fetch_film_info(film_id):
    try:
        query = """
            SELECT FilmID, Title, Year, Genre, Description, Stage_of_production, Budget
            FROM Film
            WHERE FilmID = :id
        """
        cursor = g.conn.execute(text(query), id=film_id)
        film_info = cursor.fetchone()
        return film_info
    finally:
        cursor.close()


def fetch_school_info_by_film(film_id):
    try:
        query = """
            SELECT School.Name, School.Location
            FROM School
            JOIN Film ON School.SchoolID = Film.SchoolID
            WHERE Film.FilmID = :id
        """
        cursor = g.conn.execute(text(query), id=film_id)
        school_info = cursor.fetchone()
        return school_info
    finally:
        cursor.close()

@app.route('/register_film', methods=['POST'])
def register_film():
    try:
        film_id = request.form.get('filmID')
        title = request.form.get('title')
        year = request.form.get('year')
        genre = request.form.get('genre')
        description = request.form.get('description')
        stage_of_production = request.form.get('stageOfProduction')
        budget = request.form.get('budget')
        school_id = request.form.get('schoolID')

        # Validate school_id format
        if not re.match(r'^2\d{7}$', film_id):
            error_message = "Error: Film ID must be an 8-digit number starting with 2."
            return render_template('fiilmmaker.html', error_message=error_message, film_info=None, film_not_found=True)


        # Validate film_id format
        if not film_id or not film_id.isdigit():
            error_message = "Error: Film ID must be a valid number."
            return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

        # Check if the filmID already exists
        if film_id_exists(film_id):
            error_message = "Error: Film ID already in use. Please choose a different ID."
            return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

        # Insert the new film into the database
        g.conn.execute(
            text("INSERT INTO Film (FilmID, Title, Year, Genre, Description, Stage_of_production, Budget, SchoolID) " +
                 "VALUES (:filmID, :title, :year, :genre, :description, :stage_of_production, :budget, :schoolID)"),
            filmID=film_id, title=title, year=year, genre=genre,
            description=description, stage_of_production=stage_of_production, budget=budget, schoolID=school_id
        )

        # Redirect to the filmmaker view page with the newly registered filmID
        return redirect(url_for('film', filmID=film_id))

    except Exception as e:
        # Handle any other exceptions that may occur during registration
        error_message = f"An error occurred during registration: {str(e)}"
        return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

@app.context_processor # ensures that all_schools is always populated
def inject_all_schools():
    all_schools = fetch_all_schools()
    return dict(all_schools=all_schools)

def fetch_all_schools():
    try:
        query = text("SELECT SchoolID, Name FROM School")
        result = g.conn.execute(query)
        schools = result.fetchall()
        return schools if schools else []  # Return an empty list if no schools are found
    finally:
        result.close()

def film_id_exists(film_id):
    try:
        query = text("SELECT EXISTS(SELECT 1 FROM Film WHERE FilmID = :filmID)")
        result = g.conn.execute(query, filmID=film_id).scalar()
        return result
    except Exception as e:
        error_message = f"Error checking film ID existence: {str(e)}"
        return False
    
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: https://flask.palletsprojects.com/en/2.0.x/api/?highlight=incoming%20request%20data

  """
  # DEBUG: this is debugging code to see what request looks like
  print(request.args)

  #
  # example of a database query 
  #
  # cursor = g.conn.execute("SELECT name FROM test")
  #g.conn.commit()

  # 2 ways to get results

  '''
  # Indexing result by column number
  names = []
  for result in cursor:
    names.append(result[0])  

  # Indexing result by column name
  names = []
  results = cursor.mappings().all()
  for result in results:
    names.append(result["name"])
  cursor.close()
 '''
  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #
  #     # creates a <div> tag for each element in data
  #     # will print:
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  #context = dict(data = names)
  context = dict(data=['grace hopper', 'alan turing', 'ada lovelace'])

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  #return render_template("index.html", **context)
  return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
#
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
@app.route('/another')
def another():
  return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  params_dict = {"name":name}
  g.conn.execute(text('INSERT INTO test(name) VALUES (:name)'), params_dict)
  g.conn.commit()
  return redirect('/')


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
