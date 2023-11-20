
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
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, session, g, redirect, Response, abort, url_for
from datetime import datetime
import re
from sqlalchemy.exc import IntegrityError

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
    return render_template('filmmaker.html')


@app.route('/student/', methods=['GET'])
def student():

    all_schools = fetch_all_schools()
    # Check if the form has been submitted

    if request.args.get('studentID', '').lower() == '':
        return render_template('student.html')
    
    if 'studentID' in request.args:
        student_id = request.args.get('studentID', '').lower()

        if student_id is None or student_id == '':
            return render_template('student.html', school_info=None, school_not_found=True)
    
        student_info = fetch_student_info(student_id)
        school_info = fetch_school_info(student_id)
        roles_info = fetch_roles_info(student_id)

        if student_info:
            return render_template('student.html', student_info=student_info, all_schools=all_schools, school_info=school_info, roles_info=roles_info)
        else:
            return render_template('student.html', student_not_found=True, all_schools=all_schools)

    return render_template('student.html', student_info = None)

def fetch_student_info(student_id):
    try:
        cursor = g.conn.execute(text("SELECT * FROM student WHERE studentID = :id"), {'id':student_id})
        student_info = cursor.fetchone()
        return student_info
    finally:
        cursor.close()
def fetch_school_info(student_id):
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

        school_id = request.form.get('schoolSelect')
        sinceDate = datetime.strptime(request.form.get('sinceDate'), '%Y-%m-%d')

        if student_id_exists(studentID):
            error_message = "Error: Student ID already in use. Please choose a different ID."
            return render_template('student.html', error_message=error_message)

        result = g.conn.execute(
            text("INSERT INTO student (StudentID, Name, Age, Gender, Status, GPA) VALUES (:studentID, :name, :age, :gender, :status, :gpa) RETURNING StudentID"),
            studentID=studentID, name=name, age=age, gender=gender, status=status, gpa=gpa
        )
        new_student_id = result.fetchone()[0]

        try:
            g.conn.execute(
                text("INSERT INTO Attends (StudentID, SchoolID, Since) VALUES (:studentID, :schoolID, :sinceDate)"),
                studentID=new_student_id, schoolID=school_id, sinceDate=sinceDate
            )

        except IntegrityError as e:
            g.conn.execute(text("DELETE FROM student WHERE StudentID = :studentID"), studentID=new_student_id)

            error_message = f"An error occurred during registration: {str(e)}"
            return render_template('student.html', error_message=error_message)

        new_student_id = studentID
        return redirect(url_for('student', studentID=new_student_id))

    except Exception as e:
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

@app.route('/roles', methods=['GET'])
def roles():
    return render_template('roles.html')
   
@app.route('/all_roles', methods=['GET'])
def all_roles():
    try:
        query = """
            SELECT R.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title
                FROM Role R
                JOIN Needs N ON R.RoleID = N.RoleID
                JOIN Film F ON N.FilmID = F.FilmID;    
        """
        cursor = g.conn.execute(text(query))
        all_roles_info = cursor.fetchall()
        return render_template('roles.html', all_roles_info= all_roles_info)
    finally:
        cursor.close()

@app.route('/actor_roles', methods=['GET'])
def actor_roles():
    try:
        query = """
            SELECT R.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title,
                   A.Age, A.Gender, A.Line_Count, A.Pay
            FROM Role R
            JOIN Actor A ON R.RoleID = A.RoleID
            JOIN (
                SELECT RoleID, FilmID
                FROM Needs
            ) N ON R.RoleID = N.RoleID
            JOIN Film F ON N.FilmID = F.FilmID;
        """
        cursor = g.conn.execute(text(query))
        actor_roles_info = cursor.fetchall()
        return render_template('roles.html', actor_roles_info= actor_roles_info)
    finally:
        cursor.close()

@app.route('/producer_roles', methods=['GET'])
def producer_roles():
    try:
        query = """
            SELECT R.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title,
                    P.Type, P.In_Guild
            FROM Role R
            JOIN Producer P ON R.RoleID = P.RoleID
            JOIN (
                SELECT RoleID, FilmID
                FROM Needs
            ) N ON R.RoleID = N.RoleID
            JOIN Film F ON N.FilmID = F.FilmID;
        """
        cursor = g.conn.execute(text(query))
        producer_roles_info = cursor.fetchall()
        return render_template('roles.html', producer_roles_info= producer_roles_info)
    finally:
        cursor.close()

@app.route('/director_roles', methods=['GET'])
def director_roles():
    try:
        query = """
            SELECT R.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title,
                    D.Salary
            FROM Role R
            JOIN Director D ON R.RoleID = D.RoleID
            JOIN (
                SELECT RoleID, FilmID
                FROM Needs
            ) N ON R.RoleID = N.RoleID
            JOIN Film F ON N.FilmID = F.FilmID;
        """
        cursor = g.conn.execute(text(query))
        director_roles_info = cursor.fetchall()
        return render_template('roles.html', director_roles_info= director_roles_info)
    finally:
        cursor.close()

@app.route('/crew_roles', methods=['GET'])
def crew_roles():
    try:
        query = """
            SELECT R.RoleID, R.Description, R.Level, R.Status, R.Begin, R.Finish, F.Title,
                    C.Hourly_rate
            FROM Role R
            JOIN Crew_Member C ON R.RoleID = C.RoleID
            JOIN (
                SELECT RoleID, FilmID
                FROM Needs
            ) N ON R.RoleID = N.RoleID
            JOIN Film F ON N.FilmID = F.FilmID;
        """
        cursor = g.conn.execute(text(query))
        crew_roles_info = cursor.fetchall()
        return render_template('roles.html', crew_roles_info= crew_roles_info)
    finally:
        cursor.close()

@app.route('/school', methods=['GET'])
def school():
    
    school_id = request.args.get('schoolID')

    if school_id is None or school_id == '':
            return render_template('school.html',school_info=None, school_not_found=True)

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

        if not re.match(r'^1\d{7}$', school_id):
            error_message = "Error: School ID must be an 8-digit number starting with 1."
            return render_template('school.html', error_message=error_message, school_info=None, school_not_found=True)

        if school_id_exists(school_id):
            error_message = "Error: School ID already in use. Please choose a different ID."
            return render_template('school.html', error_message=error_message, school_info=None, school_not_found=True)

        g.conn.execute(
            text("INSERT INTO School (SchoolID, Name, Location, Description) VALUES (:schoolID, :name, :location, :description)"),
            schoolID=school_id, name=name, location=location, description=description
        )

        return redirect(url_for('school', school_id=school_id))

    except Exception as e:
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

    if film_id is None or film_id == '':
        return render_template('filmmaker.html', film_info=None, school_info=None, film_not_found=True, all_schools=[], students_info=[])
    
    
    all_schools = fetch_all_schools()

    film_info = fetch_film_info(film_id)
    school_info = fetch_school_info_by_film(film_id)
    print(school_info[2])
    students_info = fetch_students_for_school(school_info[2]) if school_info else []
    print(students_info)

    if film_info:
        return render_template('filmmaker.html', film_info=film_info, school_info=school_info, all_schools=all_schools, film_not_found=False, students_info=students_info)
    else:
        return render_template('filmmaker.html', film_info=None, school_info=None, film_not_found=True, all_schools=all_schools, students_info=students_info)
    
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
            SELECT School.Name, School.Location, School.SchoolID
            FROM School
            JOIN Film ON School.SchoolID = Film.SchoolID
            WHERE Film.FilmID = :id
        """
        cursor = g.conn.execute(text(query), id=film_id)
        school_info = cursor.fetchone()
        return school_info
    finally:
        cursor.close()

def fetch_students_for_school(school_id):
    try:
        query = """
            SELECT S.StudentID, S.Name, S.Age, S.Gender, S.Status, S.GPA
            FROM Student S
            JOIN Attends A ON S.StudentID = A.StudentID
            WHERE A.SchoolID = :school_id;
        """
        cursor = g.conn.execute(text(query), school_id=school_id)
        students_info = cursor.fetchall()
        return students_info
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

        if not re.match(r'^2\d{7}$', film_id):
            error_message = "Error: Film ID must be an 8-digit number starting with 2."
            return render_template('fiilmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

        if not film_id or not film_id.isdigit():
            error_message = "Error: Film ID must be a valid number."
            return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

        if film_id_exists(film_id):
            error_message = "Error: Film ID already in use. Please choose a different ID."
            return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

        g.conn.execute(
            text("INSERT INTO Film (FilmID, Title, Year, Genre, Description, Stage_of_production, Budget, SchoolID) " +
                 "VALUES (:filmID, :title, :year, :genre, :description, :stage_of_production, :budget, :schoolID)"),
            filmID=film_id, title=title, year=year, genre=genre,
            description=description, stage_of_production=stage_of_production, budget=budget, schoolID=school_id
        )

        return redirect(url_for('film', filmID=film_id))

    except Exception as e:
        error_message = f"An error occurred during registration: {str(e)}"
        return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

@app.route('/add_student_to_film', methods=['POST'])
def add_student_to_film():
    film_id = request.form.get('filmID')
    student_id = request.form.get('studentID')
    role_id = request.form.get('roleID')

    try:
        if not (film_id and student_id and role_id):
            error_message_2 = 'Error: Incomplete form data'
            return render_template('filmmaker.html', film_info=fetch_film_info(film_id), 
            school_info=fetch_school_info_by_film(film_id), all_schools=fetch_all_schools(), 
            students_info=fetch_students_for_school(film_id), error_message_2=error_message_2)

        print(film_id)
        print(student_id)
        print(role_id)
        if not re.match(r'^2\d{7}$', film_id) or not re.match(r'^3\d{7}$', role_id):
            error_message_2 = 'Error: Invalid ID format'
            return render_template('filmmaker.html', film_info=fetch_film_info(film_id), 
            school_info=fetch_school_info_by_film(film_id), all_schools=fetch_all_schools(), 
            students_info=fetch_students_for_school(film_id), error_message_2=error_message_2)

        result = add_student_to_film(student_id, film_id, role_id)

        if not result:
            error_message_2 = 'Error: Unable to add student to film'
            return render_template('filmmaker.html', film_info=fetch_film_info(film_id), 
            school_info=fetch_school_info_by_film(film_id), all_schools=fetch_all_schools(), 
            students_info=fetch_students_for_school(film_id), error_message_2=error_message_2)

        return render_template('filmmaker.html', film_info=fetch_film_info(film_id), 
        school_info=fetch_school_info_by_film(film_id), all_schools=fetch_all_schools(), 
        students_info=fetch_students_for_school(film_id), error_message_2=None)

    except Exception as e:
        error_message_2 = f'An error occurred: {str(e)}'
        return render_template('filmmaker.html', film_info=fetch_film_info(film_id),
         school_info=fetch_school_info_by_film(film_id), all_schools=fetch_all_schools(), 
         students_info=fetch_students_for_school(film_id), error_message_2=error_message_2)

def add_student_to_film(student_id, film_id, role_id):
    try:
        g.conn.execute(
            text("INSERT INTO Part_Of (StudentID, FilmID, RoleID) VALUES (:student_id, :film_id, :role_id)"),
            student_id=student_id, film_id=film_id, role_id=role_id
        )
        return True  
    except Exception as e:
        print(f"Error adding student to film: {str(e)}")
        return False

@app.context_processor 
def inject_all_schools():
    all_schools = fetch_all_schools()
    return dict(all_schools=all_schools)

def fetch_all_schools():
    try:
        query = text("SELECT SchoolID, Name FROM School")
        result = g.conn.execute(query)
        schools = result.fetchall()
        return schools if schools else []  
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

@app.route('/add_role', methods=['POST'])
def add_role():
    print("in add_role")
    try:
        role_id = request.form.get('roleID')  
        if not re.match(r'^3\d{7}$', role_id):
            error_message = "Error: Role ID must be an 8-digit number starting with 3."
            return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

        role_type = request.form.get('roleType')
        description = request.form.get('description')
        level = int(request.form.get('level'))
        status = int(request.form.get('status'))
        begin_date = request.form.get('beginDate')
        finish_date = request.form.get('finishDate')

        if role_type == 'Director':
            salary = float(request.form.get('salary'))
        elif role_type == 'Actor':
            age = int(request.form.get('age'))
            gender = request.form.get('gender')
            line_count = int(request.form.get('lineCount'))
            pay = float(request.form.get('pay'))
        elif role_type == 'Producer':
            producer_type = request.form.get('producerType')
            in_guild = int(request.form.get('inGuild'))
            percent_stake = float(request.form.get('percentStake'))
        elif role_type == 'Crew':
            hourly_rate = float(request.form.get('hourlyRate'))

        g.conn.execute(
            text("INSERT INTO Role (RoleID, Description, Level, Status, Begin, Finish) VALUES (:role_id, :description, :level, :status, :begin_date, :finish_date)"),
            role_id=role_id, description=description, level=level, status=status, begin_date=begin_date, finish_date=finish_date
        )

        if role_type == 'Director':
            g.conn.execute(
                text("INSERT INTO Director (RoleID, Salary) VALUES (:role_id, :salary)"),
                role_id=role_id, salary=salary
            )
        elif role_type == 'Actor':
            g.conn.execute(
                text("INSERT INTO Actor (RoleID, Age, Gender, Line_Count, Pay) VALUES (:role_id, :age, :gender, :line_count, :pay)"),
                role_id=role_id, age=age, gender=gender, line_count=line_count, pay=pay
            )
        elif role_type == 'Producer':
            g.conn.execute(
                text("INSERT INTO Producer (RoleID, Type, In_Guild, Percent_Stake) VALUES (:role_id, :producer_type, :in_guild, :percent_stake)"),
                role_id=role_id, producer_type=producer_type, in_guild=in_guild, percent_stake=percent_stake
            )
        elif role_type == 'Crew':
            g.conn.execute(
                text("INSERT INTO Crew (RoleID, Hourly_Rate) VALUES (:role_id, :hourly_rate)"),
                role_id=role_id, hourly_rate=hourly_rate
            )

        film_id = request.form.get('filmID')  
        g.conn.execute(
            text("INSERT INTO Needs (RoleID, FilmID, Posted) VALUES (:role_id, :film_id, :posted)"),
            role_id=role_id, film_id=film_id, posted=datetime.utcnow()
        )

        return redirect(url_for('film', filmID=film_id))  

    except IntegrityError as e:
        g.conn.execute(text("ROLLBACK"))
        error_message = f"An error occurred while adding the role: {str(e)}"
        return render_template('filmmaker.html', error_message=error_message, film_info=None, film_not_found=True)

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
