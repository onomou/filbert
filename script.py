from flask import (
    Flask,
    request,
    render_template,
    redirect,
    flash,
    url_for,
    send_from_directory,
    jsonify,
)
from markupsafe import Markup
from canvasapi import Canvas
from datetime import datetime
import configparser
import csv
import os
# from dash import Dash, dcc, html, Input, Output, State
# import dash_table
# import pandas as pd
from werkzeug.utils import secure_filename



def load_config(filename):
    config = configparser.ConfigParser()
    config.read(filename)
    return config


config = load_config("config.ini")

# Flask section
flask_app = Flask(__name__, static_folder="static")
flask_app.static_folder = "static"
flask_app.static_url_path = "/static"
flask_app.secret_key = "fjeioaijcvmew908jcweio320"
flask_app.config['UPLOAD_FOLDER'] = config.get('Flask', 'TEMP_DIR')#'/temp/uploads' # TODO: handle missing config key
# Ensure the upload folder exists, create it if necessary
os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)


@flask_app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(flask_app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


def render_page(template_name, **kwargs):
    return render_template(template_name, **kwargs)


"""
# Dash section
dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dash/')
# Create the layout for the Dash app
# Create some sample data
info = [
    {'a1': 'a1 value', 'b1': 'b1 value', 'c1': 'c1 value', 'd1': 'd1 value'},
    {'a1': 'a2 value', 'b1': 'b1 value', 'c1': 'c1 value', 'd1': 'd2 value'},
]
df = pd.DataFrame(info)

# Create the layout for the Dash app
dash_app.layout = html.Div([
    html.H1("Editable Table with Dash/Plotly"),
    dcc.Input(id='filter-input', type='text', placeholder='Filter Data'),
    dash_table.DataTable(
        id='table',
        columns=[{'name': col, 'id': col} for col in df.columns],
        data=df.to_dict('records'),  # Data for the table
        sort_action='native',       # Enable sorting
        sort_mode='multi',          # Allow multiple columns to be sorted
        column_selectable='multi',  # Allow multiple column selection
        editable=True,  # Make the table editable
    ),
])

@dash_app.callback(
    Output('table', 'data'),
    Input('table', 'sort_by'),
    State('table', 'data'),
)
def update_table(sort_by, data):
    if not sort_by:
        # No sorting applied, return the current data
        return data

    # Sort the data based on the sorting criteria
    sorted_data = sorted(data, key=lambda x: x.get(sort_by[0]['column_id']), reverse=sort_by[0]['direction'] == 'desc')

    return sorted_data
"""

# TODO: work in progress
class Cnvs:
    def __init__(self, API_URL, API_KEY):
        self.API_URL = API_URL
        self.API_KEY = API_KEY
        self.canvas = Canvas(API_URL, API_KEY)
        
    def get_course(self, course_id):
        return self.courses[course_id]

#

# Canvas section
API_URL = config.get("Canvas", "API_URL") # TODO: handle missing config key
API_KEY = config.get("Canvas", "API_KEY") # TODO: handle missing config key
canvas = Canvas(API_URL, API_KEY)
courses = canvas.get_courses()
courses_d = {x.id: x for x in courses}
# assignments_d = {course.id:{x.id for x in course.get_assignments()} for course in courses}
# assignment_groups = {}
canvas_d = {'API_URL': API_URL,
            'API_KEY': API_KEY,
            'courses': {x.id: {'course': x} for x in courses},
            }
for course_id in canvas_d['courses'].keys():
    canvas_d['courses'][course_id]['assignments'] = {}
    canvas_d['courses'][course_id]['assignment_groups'] = {}
    canvas_d['courses'][course_id]['quizzes'] = {}
    canvas_d['courses'][course_id]['users'] = {}
    canvas_d['courses'][course_id]['enrollments'] = {}
    canvas_d['courses'][course_id]['modules'] = {}

# canvas['courses'][course_id]['assignments']
selected_course = None

def reload_assignments(course_id = None):
    target_course_ids = [course_id] if course_id is not None else canvas_d['courses'].keys()
    for course_id in target_course_ids:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['assignments'] = {x.id: {'assignment': x} for x in course.get_assignments()}
        # canvas_d['courses'][course_id]['assignment_groups'] = {x.id: {'assignment_group': x} for x in course.get_assignment_groups()}
        # canvas_d['courses'][course_id]['quizzes'] = {x.id: {'quiz': x} for x in course.get_quizzes()}
        # canvas_d['courses'][course_id]['users'] = {x.id: {'user': x} for x in course.get_users()}
        # canvas_d['courses'][course_id]['enrollments'] = {x.id: {'enrollment': x} for x in course.get_enrollments()}
        # canvas_d['courses'][course_id]['modules'] = {x.id: {'module': x} for x in course.get_modules()}



def get_courses():
    return [x['course'] for x in canvas_d['courses'].values()]
def get_course(course_id):
    course_id = int(course_id)
    return canvas_d['courses'][course_id]['course']
def get_assignments(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['assignments'] == {} or refresh:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['assignments'] = {x.id: {'assignment': x} for x in course.get_assignments()}
        print('refresh assignments: ' + str(course_id))
    return [x['assignment'] for x in canvas_d['courses'][course_id]['assignments'].values()]
def get_assignment(course_id, assignment_id):
    course_id = int(course_id)
    assignment_id = int(assignment_id)
    if assignment_id not in canvas_d['courses'][course_id]['assignments']:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['assignments'][assignment_id] = {'assignment': course.get_assignment(assignment_id)}
        print('missed assignment ' + str(assignment_id) + ' in course ' + str(course_id))
    return canvas_d['courses'][course_id]['assignments'][assignment_id]['assignment']
def get_assignment_groups(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['assignment_groups'] == {} or refresh:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['assignment_groups'] = {x.id: {'assignment_group': x} for x in course.get_assignment_groups()}
        print('refresh assignment groups: ' + str(course_id))
    return [x['assignment_group'] for x in canvas_d['courses'][course_id]['assignment_groups'].values()]
def get_modules(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['modules'] == {} or refresh:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['modules'] = {x.id: {'module': x, 'module_items': {y.id: y for y in x.get_module_items()}} for x in course.get_modules()}
        print('refresh modules: ' + str(course_id))
    return [x['module'] for x in canvas_d['courses'][course_id]['modules'].values()]
def get_module(course_id, module_id):
    course_id = int(course_id)
    module_id = int(module_id)
    if module_id not in canvas_d['courses'][course_id]['modules']:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['modules'][module_id] = {'module': course.get_module(module_id)}
        print('missed module ' + str(module_id) + ' in course ' + str(course_id))
    return canvas_d['courses'][course_id]['modules'][module_id]['module']
def get_module_items(course_id, module_id):
    return canvas_d['courses'][course_id]['modules'][module_id]['module_items']
def get_quizzes(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['quizzes'] == {} or refresh:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['quizzes'] = {x.id: {'quiz': x} for x in course.get_quizzes()}
        print('refresh quizzes: ' + str(course_id))
    return [x['quiz'] for x in canvas_d['courses'][course_id]['quizzes'].values()]
def get_quiz(course_id, quiz_id):
    course_id = int(course_id)
    quiz_id = int(quiz_id)
    if quiz_id not in canvas_d['courses'][course_id]['quizzes']:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['quizzes'][quiz_id] = {'quiz': course.get_quiz(quiz_id)}
        print('missed quiz ' + str(quiz_id) + ' in course ' + str(course_id))
    return canvas_d['courses'][course_id]['quizzes'][quiz_id]['quiz']
def get_users(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['users'] == {} or refresh:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['users'] = {x.id: {'user': x} for x in course.get_users()}
        print('refresh users: ' + str(course_id))
    return [x['user'] for x in canvas_d['courses'][course_id]['users'].values()]

# reload_assignments()
# _ = get_assignments()

# Template context globals
@flask_app.template_global()
def all_courses():
    return courses_d.values()


# Routes section
@flask_app.route("/", methods=["GET", "POST"])
def index():
    global courses_d, selected_course

    return render_template(
        "form.html", selected=selected_course
    )

# refresh everything
@flask_app.route("/refresh", methods=["GET"])
def refresh_everything():
    flash('trying to refresh')
    reload_assignments()
    flash('Reloaded everything')
    return redirect(request.referrer)

@flask_app.route("/course", methods=["GET"])
def course_redirect():
    course_id = request.args.get("course_id")
    return redirect(f"/{course_id}")


@flask_app.route("/course/<int:course_id>/<action>", methods=["GET"])
def course_action(course_id, action):
    if action == "new_assignment":
        return redirect(f"/course/{course_id}/new_assignment")
    elif action == "list_quiz":
        return redirect(f"/course/{course_id}/quiz")


@flask_app.route("/course/<int:course_id>/assignment", methods=["GET"])
def list_assignments(course_id):
    global courses_d, canvas_d  # , assignment_groups
    course = courses_d[course_id]
    assignments = get_assignments(course_id)#course.get_assignments()
    assignment_groups = course.get_assignment_groups()
    modules = course.get_modules()

    return render_page(
        "assignment.html",
        active_course=course,
        assignment=None,
        assignments=assignments,
        categories=assignment_groups,
        modules=modules,
        action="assignment",
    )


@flask_app.route("/course/<int:course_id>/assignment/refresh", methods=["GET"])
def refresh_assignments(course_id):
    get_assignments(course_id, True)
    return redirect(request.referrer)


@flask_app.route("/course/<int:course_id>/assignment/<int:assignment_id>", methods=["GET"])
def assignment(course_id, assignment_id):
    global courses_d, canvas_d  # , assignment_groups
    course = canvas_d['courses'][course_id]['course']
    assignment = get_assignment(course_id, assignment_id)
    assignments = get_assignments(course_id)#course.get_assignments()
    assignment_groups = get_assignment_groups(course_id)#course.get_assignment_groups()
    modules = get_modules(course_id)#course.get_modules()
    module_items = {module.id:get_module_items(course_id, module.id) for module in modules}#{'module': x['module'], 'module_items': x['module_items']
    assignment_modules = []#set(x.id for x, y in module_items.items())
    groups_count = min(5, max(len(list(assignment_groups)), len(list(modules))))
    for module_id, module_items in module_items.items():
        for module_item in module_items.values():
            if module_item.type in ['File', 'Discussion', 'Assignment', 'Quiz', 'ExternalTool'] and module_item.content_id == assignment_id:
                assignment_modules.append(module_id)
    print(assignment_modules)

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        flash('This feature is not yet implemented.')
        return redirect(request.referrer)
    

    # return redirect(f"/course/{course_id}/new_assignment")
    # return redirect(API_URL + '/courses/' + str(course_id) + '/assignments/' + str(assignment_id))

    return render_page(
        "assignment.html",
        active_course=course,
        assignment=assignment,
        assignments=assignments,
        categories=assignment_groups,
        modules=modules,
        assignment_modules=assignment_modules,
        groups_count=groups_count,
        action="assignment",
    )


@flask_app.route("/course/<int:course_id>/new_assignment", methods=["GET", "POST"])
def course_page(course_id):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)#courses_d[course_id]
    assignments = get_assignments(course_id)#course.get_assignments()
    modules = get_modules(course_id)#course.get_modules()

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        # insert latex equations eg. https://canvas.instructure.com/equation_images/4n-1?scale=1

        #attach_file = request.form.get("attach")
        #if attach_file != "" or True:
        if 'file' in request.files:
            print('file attached to POST')
            file = request.files['file']
            if file.filename == '':
                # no file attached
                print('no file selected')
            else:
                filename = secure_filename(file.filename)
                print('filename: ' + filename)
                the_filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
                # print(the_filepath)
                # file.save(the_filepath)
                file.save(the_filepath)
                # print(url_for('download_file', name=filename))
                result = course.upload(the_filepath, parent_folder_path='Uploaded Media')
                if result[0] is True:
                    canvas_file = result[1]
                    print('uploaded file ' + canvas_file['display_name'])
                    #print(result)
                    # print('resut != "": ' + str(attach_file != ""))
                    description += '<p><a class="instructure_file_link instructure_scribd_file auto_open"'\
                        + ' title="' + canvas_file['display_name'] + '"'\
                        + ' href="' + API_URL + '/courses/' + str(course.id) + '/files/' + str(canvas_file['id'])\
                        + '?wrap=1 target="_blank" rel="noopener" data-canvas-previewable="false">'\
                        + canvas_file["display_name"] + '</a></p>'
                        # data-api-endpoint="https://canvas.instructure.com/api/v1/courses/7675174/files/228895639"\
                        #     data-api-returntype="File">\
        
        points = request.form.get("points")
        print("points is " + str(points) + " and type is " + str(type(points)))
        due_date_text = request.form.get("due_date")
        try:
            due_date = datetime.strptime(
                due_date_text, "%Y-%m-%d %H:%M"
            )  # '2023-08-30 15:00'
        except:
            due_date = None
        published = request.form.get("published")
        category = request.form.get("category")
        assignment = course.create_assignment(
            assignment={
                "name": name,
                "description": description,
                "points_possible": points,
                "due_at": due_date,
                "published": published,
                "assignment_group_id": category,
            }
        )
        selected_module_ids = request.form.getlist("modules")
        selected_modules = []
        created_module_items = []
        print(selected_module_ids)
        for module_id in selected_module_ids:
            module = get_module(course_id, module_id)#course.get_module(module_id)
            selected_modules.append(module)
            print(module.name)
            module_item = module.create_module_item(
                module_item={
                    "type": "assignment",
                    "content_id": assignment.id,
                    "position": module.items_count+1,
                }
            )
            created_module_items.append(module_item)
        flash(
            "Assignment created and added to these modules: "
            + ", ".join(module.name for module in selected_modules)
        )
        assignment_link = (
            '<br><a href="'
            + assignment.html_url
            + '" target="_blank" rel="noopener noreferrer">'
            + assignment.name
            + "</a>"
        )
        flash(Markup(assignment_link), "info")
        # return redirect(url_for('/course/'+course_id+'/new_assignment'))
        # return# redirect(url_for('index'))
        return redirect(request.referrer)

    # Retrieve assignment categories from Canvas
    # assignment_groups = course.get_assignment_groups()  # Fetch assignment groups for the selected course
    assignment_groups = get_assignment_groups(course_id)

    groups_count = min(5, max(len(list(assignment_groups)), len(list(modules))))

    # tinymce_key = config.get("TinyMCE", "API_KEY") # TODO: handle missing config key

    return render_page(
        "new_assignment.html",
        active_course=course,
        assignment=None,
        assignments=assignments,
        categories=assignment_groups,
        groups_count=groups_count,
        # tinymce_api_key=tinymce_key,
        modules=modules,
        action="new_assignment",
    )


@flask_app.route("/course/<int:course_id>/new_assignment_bulk", methods=["GET", "POST"])
def new_assignment_bulk(course_id):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)#courses_d[course_id]
    modules = get_modules(course_id)#course.get_modules()

    if request.method == "POST":
        return redirect(request.referrer)
    return render_page(
        "new_assignment_bulk.html",
        active_course=course,
        quiz=None,
        modules=modules,
        action="new_assignment_bulk",
    )


@flask_app.route("/course/<int:course_id>/quiz", methods=["GET", "POST"])
def quiz_page(course_id):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)#courses_d[course_id]
    modules = get_modules(course_id)#course.get_modules()
    quizzes = get_quizzes(course_id)#course.get_quizzes()

    if request.method == "POST":
        return redirect(request.referrer)
    return render_page(
        "quiz_details.html",
        active_course=course,
        quiz=None,
        quizzes=quizzes,
        modules=modules,
        action="list_quiz",
    )


@flask_app.route("/course/<int:course_id>/quiz/<quiz_id>", methods=["GET", "POST"])
def quiz_details(course_id, quiz_id):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)#courses_d[course_id]
    modules = get_modules(course_id)#course.get_modules()
    quizzes = get_quizzes(course_id)#course.get_quizzes()
    quiz = get_quiz(course_id, quiz_id)#course.get_quiz(quiz_id)
    quiz_questions = quiz.get_questions()

    if request.method == "POST":
        return redirect(request.referrer)
    return render_page(
        "quiz_details.html",
        active_course=course,
        quiz=quiz,
        quiz_questions=quiz_questions,
        quizzes=quizzes,
        modules=modules,
        action="list_quiz",
    )


@flask_app.route(
    "/course/<int:course_id>/quiz/<quiz_id>/question/<question_id>", methods=["GET", "POST"]
)
def quiz_question_details(course_id, quiz_id, question_id):
    global courses_d  # , assignment_groups
    course = get_course(course_id)#courses_d[course_id]
    modules = get_modules(course_id)#course.get_modules()
    quizzes = get_quizzes(course_id)#course.get_quizzes()
    quiz = get_quiz(course_id, quiz_id)#course.get_quiz(quiz_id)
    quiz_questions = quiz.get_questions()
    quiz_question = quiz.get_question(question_id)

    if request.method == "POST":
        # code to update the quiz question
        question_name = request.form.get("question_name")
        question_text = request.form.get("question_text")
        position = request.form.get("position")
        points_possible = request.form.get("points_possible")
        question = quiz_question.edit(
            {
                "quiz_id": quiz.id,
                "id": question_id,
                "question_text": question_text,
                "question_name": question_name,
                "position": position,
                "points_possible": points_possible,
            }
        )

        flash("Quiz question updated!")
        return redirect(request.referrer)
    return render_page(
        "quiz_question_details.html",
        active_course=course,
        quiz=quiz,
        quiz_questions=quiz_questions,
        quiz_question=quiz_question,
        quizzes=quizzes,
        modules=modules,
        action="quiz_question_details",
    )

@flask_app.route(
    "/course/<int:course_id>/quiz/<quiz_id>/question/<question_id>/download", methods=["POST"]
)
def quiz_question_download(course_id, quiz_id, question_id):
    question_id = int(question_id)
    global courses_d
    course = get_course(course_id)#canvas.get_course(course_id)
    users = get_users(course_id)#course.get_users()
    users_d = {x.id:x for x in users}
    quiz = get_quiz(course_id, quiz_id)#course.get_quiz(quiz_id)
    quiz_questions = quiz.get_questions()
    quiz_questions_d = {x.id:x for x in quiz_questions}
    quiz_question = quiz_questions_d[question_id]
    assignment = get_assignment(course_id, quiz.assignment_id)#course.get_assignment(quiz.assignment_id)
    submissions = assignment.get_submissions(include=['submission_history'])
    
    # gather all responses
    all_responses = {}
    for submission in submissions:
        latest_attempt = max(submission.submission_history, key=lambda x: x['attempt'])
        submission_data = latest_attempt.get('submission_data', None)
        if submission_data is not None:
            response = [x for x in submission_data if x['question_id'] == question_id]
            if len(response) > 0:
                response = response[0]
                key = str(response['question_id']) + str(submission.user_id)
                all_responses[key] = {
                    'question_id': str(response['question_id']),
                    'position': str(quiz_questions_d[response['question_id']].position),
                    'question_text': str(quiz_questions_d[response['question_id']].question_text).replace('\n','\\n'),
                    'user_id': str(submission.user_id),
                    'attempt': str(submission.attempt),
                    'correct': str(response['correct']),
                    'points': str(float(response['points'])), # necessary because 0 -> 0 but 1 -> 1.0
                    'text': response['text'].replace('\n','\\n'),
                    #'new_score': '',
                    'comment': '',
                }
                if quiz_questions_d[response['question_id']].question_type == 'fill_in_multiple_blanks_question':
                    for k, v in response.items():
                        # if '_for_' in k: # matches all answer_for_blankX'
                        if 'answer_' in k: # matches all answer_for_blankX'
                            all_responses[key][k] = str(v)
    
    filename = str(course.id) + '-quiz-' + str(assignment.quiz_id) + '-question-' + str(question_id) + '-responses.csv'
    filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        list_of_dict_keys = [x.keys() for x in all_responses.values()]
        fieldnames = list({n:'' for n in [i for s in [list(x) for x in list_of_dict_keys] for i in s]}.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        data = sorted(all_responses.values(), key=lambda x: (int(-1 if x['position'] == 'None' else x['position']), x['question_id'], x['correct'], x['points'], x['text']))
        writer.writerows(data)

    return send_from_directory(flask_app.config['UPLOAD_FOLDER'], filename)#redirect(request.referrer)

@flask_app.route(
    "/course/<int:course_id>/quiz/<quiz_id>/question/<question_id>/upload", methods=["POST"]
)
def quiz_question_upload(course_id, quiz_id, question_id):
    question_id = int(question_id)
    global courses_d
    course = get_course(course_id)#canvas.get_course(course_id)
    users = get_users(course_id)#course.get_users()
    users_d = {x.id:x for x in users} # TODO: fix this
    quiz = get_quiz(quiz_id)#course.get_quiz(quiz_id)
    quiz_questions = quiz.get_questions()
    quiz_questions_d = {x.id:x for x in quiz_questions}
    quiz_question = quiz_questions_d[question_id]
    assignment = get_assignment(quiz.assignment_id)#course.get_assignment(quiz.assignment_id)
    submissions = assignment.get_submissions(include=['submission_history'])
    
    # gather all responses
    all_responses = {}
    for submission in submissions:
        latest_attempt = max(submission.submission_history, key=lambda x: x['attempt'])
        submission_data = latest_attempt.get('submission_data', None)
        if submission_data is not None:
            response = [x for x in submission_data if x['question_id'] == question_id]
            if len(response) > 0:
                response = response[0]
                key = str(response['question_id']) + str(submission.user_id)
                all_responses[key] = {
                    'question_id': str(response['question_id']),
                    'position': str(quiz_questions_d[response['question_id']].position),
                    'question_text': str(quiz_questions_d[response['question_id']].question_text).replace('\n','\\n'),
                    'user_id': str(submission.user_id),
                    'attempt': str(submission.attempt),
                    'correct': str(response['correct']),
                    'points': str(float(response['points'])), # necessary because 0 -> 0 but 1 -> 1.0
                    'text': response['text'].replace('\n','\\n'),
                    #'new_score': '',
                    'comment': '',
                }
                if quiz_questions_d[response['question_id']].question_type == 'fill_in_multiple_blanks_question':
                    for k, v in response.items():
                        # if '_for_' in k: # matches all answer_for_blankX'
                        if 'answer_' in k: # matches all answer_for_blankX'
                            all_responses[key][k] = str(v)
    
    # filename = str(course.id) + '-quiz-' + str(assignment.quiz_id) + '-question-' + str(question_id) + '-original.csv'
    # filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
    # with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
    #     list_of_dict_keys = [x.keys() for x in all_responses.values()]
    #     fieldnames = list({n:'' for n in [i for s in [list(x) for x in list_of_dict_keys] for i in s]}.keys())
    #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #     writer.writeheader()
    #     data = sorted(all_responses.values(), key=lambda x: (int(-1 if x['position'] == 'None' else x['position']), x['question_id'], x['correct'], x['points'], x['text']))
    #     writer.writerows(data)
    

    filename = str(course.id) + '-quiz-' + str(assignment.quiz_id) + '-question-' + str(question_id) + '-responses.csv'
    filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
    all_responses_graded = []
    with open(filepath, newline='\r\n', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        #example_types = next(iter(all_responses.values()))
        for row in reader:
            #for key, val in row.items():
            #    row[key] = type(example_types[key])(val)
            all_responses_graded.append(row)
        
    # match row with original
    new_data = []
    flash_message = []
    for x in all_responses_graded:
        original = all_responses.get(str(x['question_id']) + str(x['user_id']), None)
        editable_fields = ['points', 'comment']
        if original is not None:
            # https://stackoverflow.com/questions/32815640/how-to-get-the-difference-between-two-dictionaries-in-python
            o_set = set({k: v for k, v in original.items() if k in editable_fields}.items())
            n_set = set({k: v for k, v in x.items() if k in editable_fields}.items())
            o_data = o_set - n_set
            n_data = n_set - o_set
            if o_data != set() or n_data != set():
                flash_message.append(['old: ' + str(o_data) + '\nnew: ' + str(n_data) + '\n'])
                n_data.update([('question_id', original['question_id']), ('user_id', original['user_id']), ('attempt', original['attempt'])])
                new_data.append(dict(n_data))
    flash(flash_message)

    updates = {}
    for x in new_data:
        updates.setdefault(x['user_id'], {})
        updates[x['user_id']].setdefault('attempt', x['attempt'])
        updates[x['user_id']].setdefault('fudge_points', 0)
        updates[x['user_id']].setdefault('questions', {})
        updates[x['user_id']]['questions'][x['question_id']] = {
            'score': x.get('points', None),
            'comment': x.get('comment', None)
        }
        #if 'points' not in x:
        #    print('you should check on this one: ' + str(x['user_id']) + ', question: ' + str(x['question_id']))

    quiz_submissions = quiz.get_submissions()
    quiz_submissions_d = {x.user_id:x for x in quiz_submissions}

    updated_submissions = []
    results = []
    for user_id, feedback in updates.items():
        quiz_submission = quiz_submissions_d[int(user_id)]
        result = quiz_submission.update_score_and_comments(quiz_submissions=[feedback])
        updated_submissions.append(result)
        results.append(['score: ' + str(result.score) + ' kept: ' + str(result.kept_score) + ' url: ' + result.html_url + ' user: ' + users_d[result.user_id].name])
    flash(results)
    return redirect(request.referrer)


"""
@flask_app.route('/course/<int:course_id>/assignments/dash', methods=['GET', 'POST'])
def go_dash(course_id):
    return redirect('/dash/')
"""


def get_assignment_data(course_id):
    course = courses_d[course_id]
    assignments = get_assignments(course_id)#course.get_assignments()
    data = [{'id': x.id, 'name': x.name, 'points': x.points_possible, 'published': x.published} for x in assignments]
    return data


@flask_app.route("/course/<int:course_id>/assignments/grid", methods=["GET", "POST"])
def assignments_grid(course_id):
    global courses_d
    course = courses_d[course_id]
    assignments = get_assignments(course_id)#course.get_assignments()
    data = [{'id': x.id, 'name': x.name, 'points_possible': x.points_possible, 'published': x.published} for x in assignments]
    columns = [{'id': x, 'name': x, 'field': x} for x in data[0].keys()]
    return render_page("assignments_grid.html", active_course=course, data=data, columns=columns)



@flask_app.route("/course/<int:course_id>/assignments/update_data", methods=["POST"])
def update_assignments(course_id):
    global courses_d
    updated_data = request.get_json()  # Get the updated data sent from the client
    # Handle the updated data, e.g., update your database
    print(updated_data)
    # Return a response to the client
    return jsonify({'message': 'Data updated successfully'})




if __name__ == "__main__":
    flask_app.run(debug=True)
