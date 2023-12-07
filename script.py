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
import dateutil.parser
import pytz
import configparser
import csv
import os
from werkzeug.utils import secure_filename


def load_config(filename):
    config = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
    config.read(filename)
    return config


config = load_config("config.ini")

# Flask section
flask_app = Flask(__name__, static_folder="static")
flask_app.static_folder = "static"
flask_app.static_url_path = "/static"
flask_app.secret_key = "fjeioaijcvmew908jcweio320"
flask_app.config['UPLOAD_FOLDER'] = config.get('Flask', 'TEMP_DIR', fallback='.\\temp') # TODO: handle missing config key
# Ensure the upload folder exists; create it if necessary
os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)

from util import ListConverter
flask_app.url_map.converters['list'] = ListConverter



@flask_app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(flask_app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


def render_page(template_name, **kwargs):
    return render_template(template_name, **kwargs)


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


# canvas helper dict functions
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
        # canvas_d['courses'][course_id]['assignments'][assignment_id] = {'assignment': course.get_assignment(assignment_id)}
        get_assignments(course_id, True)
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
        for module in course.get_modules():
            get_module(course_id, module.id, True)
        # canvas_d['courses'][course_id]['modules'] = {x.id: {'module': x, 'module_items': {y.id: y for y in x.get_module_items()}} for x in course.get_modules()}
        print('refresh modules: ' + str(course_id))
    return [x['module'] for x in canvas_d['courses'][course_id]['modules'].values()]
def get_module(course_id, module_id, refresh=False):
    course_id = int(course_id)
    module_id = int(module_id)
    if module_id not in canvas_d['courses'][course_id]['modules'] or refresh:
        course = canvas_d['courses'][course_id]['course']
        module = course.get_module(module_id)
        canvas_d['courses'][course_id]['modules'][module_id] = {'module': module, 'module_items': {module_item.id: module_item for module_item in module.get_module_items()}}
        print('missed module ' + str(module_id) + ' in course ' + str(course_id))
    return canvas_d['courses'][course_id]['modules'][module_id]['module']
def get_assignment_module_ids(course_id, assignment_id, refresh=False):
    course_id = int(course_id)
    if assignment_id is None:
        return []
    assignment_id = int(assignment_id)
    assignment = get_assignment(course_id, assignment_id)
    quiz_id = getattr(assignment, 'quiz_id', -1)
    modules = get_modules(course_id, refresh)
    assignment_modules = []#set(x.id for x, y in module_items.items())
    module_items_dict = {module.id:get_module_items(course_id, module.id, refresh) for module in modules}#{'module': x['module'], 'module_items': x['module_items']
    for module_id, module_items in module_items_dict.items():
        for module_item in module_items.values():
            if module_item.type in ['File', 'Discussion', 'Assignment', 'Quiz', 'ExternalTool'] and module_item.content_id in [assignment_id, quiz_id]:
                assignment_modules.append(module_id)
    return assignment_modules
def get_module_items(course_id, module_id, refresh=False):
    course_id = int(course_id)
    module_id = int(module_id)
    if refresh:
        get_module(course_id, module_id, True)
    return canvas_d['courses'][course_id]['modules'][module_id]['module_items']
def get_quizzes(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['quizzes'] == {} or refresh:
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['quizzes'] = {x.id: {'quiz': x} for x in course.get_quizzes()}
        print('refresh quizzes: ' + str(course_id))
    return [x['quiz'] for x in canvas_d['courses'][course_id]['quizzes'].values()]
def get_quiz(course_id, quiz_id, refresh=False):
    course_id = int(course_id)
    quiz_id = int(quiz_id)
    if quiz_id not in canvas_d['courses'][course_id]['quizzes'] or refresh:
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

def get_times(course_id):
    course_id = str(course_id)
    course_times = config.getlist(course_id, "DUE_TIMES", fallback=[])
    default_times = config.getlist('DEFAULTS', "DUE_TIMES", fallback=[])
    shared_times = config.getlist('DEFAULTS', "SHARED_TIMES", fallback=[])

    all_times = course_times + shared_times
    if course_times == []:
        all_times += default_times
    return sorted(list(set(all_times)))
    if course_id in default_times:
        return default_times[course_id] + default_times['shared']
    else:
        return default_times['default'] + default_times['shared']
    
def get_submission_types(course_id):
    course_id = str(course_id)
    submission_types = config.getlist(course_id, "SUBMISSION_TYPES", fallback=[])
    return submission_types
    
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


@flask_app.route("/courses/<int:course_id>/<action>", methods=["GET"])
def course_action(course_id, action):
    match action:
        case 'assignments':
            return redirect(f"/courses/{course_id}/assignments")
        case "list_quiz":
            return redirect(f"/courses/{course_id}/quizzes")
        case 'assignments_bulk':
            return redirect(f'/courses/{course_id}/assignments_bulk')
        case 'list_quiz':
            return redirect(f'/courses/{course_id}/list_quiz')
        case 'quiz_question_details':
            return redirect(f'/courses/{course_id}/quiz_question_details')


@flask_app.route("/courses/<int:course_id>/assignment_default", methods=["GET"])
def list_assignments(course_id):
    global courses_d, canvas_d  # , assignment_groups
    course = courses_d[course_id]
    assignments = get_assignments(course_id)
    assignment_groups = course.get_assignment_groups()
    modules = course.get_modules()
    return render_page(
        "assignment.html",
        active_course=course,
        assignment=None,
        assignments=assignments,
        assignment_groups=assignment_groups,
        modules=modules,
        action="assignments",
    )


@flask_app.route("/courses/<int:course_id>/assignments/refresh", methods=["GET"])
def refresh_assignments(course_id):
    _ = get_assignments(course_id, True)
    _ = get_modules(course_id, True)
    _ = get_assignment_groups(course_id, True)
    return redirect(request.referrer)

@flask_app.route("/courses/<int:course_id>/assignments/<int:assignment_id>/delete", methods=["POST"])
def delete_assignment(course_id, assignment_id):
    assignment = get_assignment(course_id, assignment_id)
    result = assignment.delete()
    flash('Deleted assignment ' + str(assignment_id))
    refresh_assignments(course_id)
    return redirect(url_for('assignments', course_id=course_id))


# call with assignment_id=0 to create new
@flask_app.route("/courses/<int:course_id>/assignments/<int:assignment_id>/update", methods=["POST"])
def update_assignment(course_id, assignment_id=0):
    global canvas_d
    course = canvas_d['courses'][course_id]['course']
    fields = ['name', 'description', 'points_possible', 'due_at', 'published', 'assignment_group_id']
    response = {x: request.form.get(x) for x in fields}
    response['description'] = response['description'].replace('\r\n', '\n')
    response['published'] = bool(response['published'])
    response['submission_types'] = request.form.getlist('submission_types') or ['none']
    
    # handle due_at separately
    due_at_text = request.form.get("due_at")
    try:
        due_at = pytz.timezone(course.time_zone).localize(dateutil.parser.parse(due_at_text)).astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    except:
        due_at = None
    response['due_at'] = due_at

    # TODO: insert latex equations eg. https://canvas.instructure.com/equation_images/4n-1?scale=1

    # handle file attachment
    # raise(Exception)
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
                response['description'] += '<p><a class="instructure_file_link instructure_scribd_file auto_open"'\
                    + ' title="' + canvas_file['display_name'] + '"'\
                    + ' href="' + API_URL + '/courses/' + str(course.id) + '/files/' + str(canvas_file['id'])\
                    + '?wrap=1 target="_blank" rel="noopener" data-canvas-previewable="false">'\
                    + canvas_file["display_name"] + '</a></p>'
                    # data-api-endpoint="https://canvas.instructure.com/api/v1/courses/7675174/files/228895639"\
                    #     data-api-returntype="File">\
    
    if assignment_id == 0:
        # create new assignment
        assignment = course.create_assignment(
            assignment=response
        )
    else:
        # update existing assignment
        changes = {}
        assignment = get_assignment(course_id, assignment_id)
        # get differences between original and new data
        for key, val in response.items():
            if str(getattr(assignment,key)) != str(val):
                changes[key] = {'old': getattr(assignment,key), 'new': val}
        if changes == {}:
            flash('Nothing has been changed for this assignment!')
        else:
            assignment.edit(assignment={key: val['new'] for key, val in changes.items()})
            flash('Changed these things:')
            for field, change in changes.items():
                flash('<em>' + field + '</em>: ' + str(change))

    if assignment is not None:
        # add assignment to selected modules
        assignment_modules = get_assignment_modules(assignment.course_id, assignment.id)
        selected_module_ids = request.form.getlist("modules")
        # TODO: split selected_module_ids into insertions and deletions, and handle each
        module_insertions = set([x for x in selected_module_ids if x not in assignment_modules])
        print('will add to ' + str(module_insertions))
        module_deletions = set([x for x in assignment_modules if x not in selected_module_ids])
        print('will delete from ' + str(module_deletions))
        selected_modules = []
        created_module_items = []
        print(selected_module_ids)
        for module_id in module_insertions:
            module = get_module(course_id, module_id)
            selected_modules.append(module)
            print(module.name)
            module_item = module.create_module_item(
                module_item={
                    "type": "assignment",
                    "content_id": assignment.id,
                    "position": module.items_count+1,
                }
            )
            created_module_items.append(module)
        deleted_module_items = []
        for module_id in module_deletions:
            module = get_module(course_id, module_id)
            module_items = get_module_items(course_id, module_id)
            for module_item in module_items.values():
                print(str(getattr(module_item,'content_id',0)) + ' vs ' + str(module_id) + ' is ' + str(getattr(module_item,'content_id',0) == module_id))
                if getattr(module_item,'content_id',0) == assignment.id:
                    module_item.delete()
                    deleted_module_items.append(module.name)
        flash(
            "Assignment added to these modules: "
            + ", ".join(module.name for module in created_module_items)
            + '\n and removed from these modules: '
            + ','.join(module_name for module_name in deleted_module_items)
        )

        return redirect(f"/courses/{course_id}/assignments/{assignment.id}")
    else:
        flash('This feature is not yet implemented.')
        return redirect(request.referrer)

@flask_app.route("/courses/<int:course_id>/assignments", methods=["GET"], strict_slashes=False)
@flask_app.route("/courses/<int:course_id>/assignments/new", methods=["GET"], strict_slashes=False)
@flask_app.route("/courses/<int:course_id>/assignments/<int:assignment_id>", methods=["GET"])
def assignment(course_id, assignment_id=None):
    global courses_d, canvas_d  # , assignment_groups
    course = get_course(course_id)#canvas_d['courses'][course_id]['course']
    if assignment_id is None:
        # creating new assignment
        assignment = None
    else:
        try:
            assignment = get_assignment(course_id, assignment_id)
        except:
            assignment = None # TODO: redirect to /assignments

    assignments = sorted(get_assignments(course_id), key=lambda x: getattr(x,'due_at','') or '')
    for x in assignments:
        x.safe_description = Markup(x.description)
        if x.due_at is not None:
            x.due_at_local = dateutil.parser.parse(x.due_at).astimezone(pytz.timezone(course.time_zone)).strftime('%Y-%m-%d %H:%M')
            x.short_date = dateutil.parser.parse(x.due_at).astimezone(pytz.timezone(course.time_zone)).strftime('%Y-%m-%d')
    assignment_groups = get_assignment_groups(course_id)
    modules = get_modules(course_id)
    
    groups_count = min(int(config.get('DEFAULT', 'MIN_LINES', fallback=5)), max(len(list(assignment_groups)), len(list(modules))))
    
    assignment_modules = get_assignment_modules(course_id, assignment_id)
    # raise(Exception)
    # print(assignment_modules)
    # return redirect(f"/courses/{course_id}/new_assignment")
    # return redirect(API_URL + '/courses/' + str(course_id) + '/assignments/' + str(assignment_id))
    default_times = get_times(course_id)
    default_submission_types = get_submission_types(course_id)
    # print('check this out: ' + str(default_times))
    # print(assignment.description)
    submission_types = ['discussion_topic', 'online_quiz', 'on_paper', #'none',
                        'external_tool', 'online_text_entry', 
                        'online_url', 'online_upload', 'media_recording', 
                        'student_annotation']
    return render_page(
        "assignment.html",
        active_course=course,
        assignment=assignment,
        assignments=assignments,
        assignment_groups=assignment_groups,
        modules=modules,
        assignment_modules=assignment_modules,
        groups_count=groups_count,
        default_times=default_times,
        default_submission_types=default_submission_types,
        submission_types=submission_types,
        action="assignments",
    )


@flask_app.route("/courses/<int:course_id>/assignments_bulk/intersect/")
@flask_app.route("/courses/<int:course_id>/assignments_bulk/intersect/<list:assignment_ids>", methods=["GET"])
def get_selected_assignments(course_id, assignment_ids=[]):
    assignments = []
    for x in assignment_ids:
        assignments.append(get_assignment(course_id, x))
    response = {}
    
    fields = ['name', 'description', 'points_possible', 'due_at', 'published', 'assignment_group_id']
    special_fields = ['submission_types']
    for field in fields:
        # response[field] = set.intersection(*set([getattr(x,field) for x in assignments]))
        field_values = [getattr(y, field) for y in assignments]
        unique_value = list(set([x for x in field_values if (field_values.count(x) == len(field_values))]))
        response[field] = '<varies>' if len(unique_value) == 0 else unique_value[0]
    for field in special_fields:
        pass
    
    # raise(Exception)
    print('in get_selected_assignments')
    print(response)
    return response
    # return {'what': 'who'}



@flask_app.route("/courses/<int:course_id>/assignments_bulk/update/<list:assignment_ids>", methods=["POST"])
def assignments_bulk_update(course_id,assignment_ids=[]):
    # TODO: implement this
    return redirect(request.referrer)

@flask_app.route("/courses/<int:course_id>/assignments_bulk/delete/<list:assignment_ids>", methods=["POST"])
def assignments_bulk_delete(course_id,assignment_ids=[]):
    # TODO: implement this
    return redirect(request.referrer)
    
@flask_app.route("/courses/<int:course_id>/assignments_bulk", methods=["GET"], strict_slashes=False)
@flask_app.route("/courses/<int:course_id>/assignments_bulk/<list:assignment_ids>", methods=["GET"])
def assignments_bulk(course_id,assignment_ids=[]):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)
    modules = get_modules(course_id)
    assignments = sorted(get_assignments(course_id), key=lambda x: getattr(x,'due_at','') or '')
    print(assignment_ids)
    selected_assignments = []
    for x in assignment_ids:
        try:
            a = get_assignment(course_id, x)
            print(a.id)
            selected_assignments.append(a)
        except:
            pass
    assignment_ids = [x.id for x in selected_assignments]

    return render_page(
        "assignments_bulk.html",
        active_course=course,
        assignments=assignments,
        selected_assignments=selected_assignments,
        selected_assignment_ids=assignment_ids,
        quiz=None,
        modules=modules,
        action="assignments_bulk",
    )


@flask_app.route("/courses/<int:course_id>/quizzes", methods=["GET", "POST"])
def quiz_page(course_id):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)
    modules = get_modules(course_id)
    quizzes = get_quizzes(course_id)

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


@flask_app.route("/courses/<int:course_id>/quizzes/<quiz_id>", methods=["GET", "POST"])
def quiz_details(course_id, quiz_id):
    global courses_d  # , assignment_groups
    # course = canvas.get_course(course_id)
    course = get_course(course_id)
    modules = get_modules(course_id)
    quizzes = get_quizzes(course_id)
    quiz = get_quiz(course_id, quiz_id)
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
    "/courses/<int:course_id>/quizzes/<quiz_id>/question/<question_id>", methods=["GET", "POST"]
)
def quiz_question_details(course_id, quiz_id, question_id):
    global courses_d  # , assignment_groups
    course = get_course(course_id)
    modules = get_modules(course_id)
    quizzes = get_quizzes(course_id)
    quiz = get_quiz(course_id, quiz_id)
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
    "/courses/<int:course_id>/quizzes/<quiz_id>/question/<question_id>/download", methods=["POST"]
)
def quiz_question_download(course_id, quiz_id, question_id):
    question_id = int(question_id)
    global courses_d
    course = get_course(course_id)
    users = get_users(course_id)
    users_d = {x.id:x for x in users}
    quiz = get_quiz(course_id, quiz_id)
    quiz_questions = quiz.get_questions()
    quiz_questions_d = {x.id:x for x in quiz_questions}
    quiz_question = quiz_questions_d[question_id]
    assignment = get_assignment(course_id, quiz.assignment_id)
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
    "/courses/<int:course_id>/quizzes/<quiz_id>/question/<question_id>/upload", methods=["POST"]
)
def quiz_question_upload(course_id, quiz_id, question_id):
    question_id = int(question_id)
    global courses_d
    course = get_course(course_id)
    users = get_users(course_id)
    users_d = {x.id:x for x in users} # TODO: fix this
    quiz = get_quiz(quiz_id)
    quiz_questions = quiz.get_questions()
    quiz_questions_d = {x.id:x for x in quiz_questions}
    quiz_question = quiz_questions_d[question_id]
    assignment = get_assignment(quiz.assignment_id)
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


def get_assignment_data(course_id):
    course = courses_d[course_id]
    assignments = get_assignments(course_id)
    data = [{'id': x.id, 'name': x.name, 'points': x.points_possible, 'published': x.published} for x in assignments]
    return data


@flask_app.route("/courses/<int:course_id>/assignments/grid", methods=["GET", "POST"])
def assignments_grid(course_id):
    global courses_d
    course = courses_d[course_id]
    assignments = get_assignments(course_id)
    data = [{'id': x.id, 'name': x.name, 'points_possible': x.points_possible, 'published': x.published} for x in assignments]
    columns = [{'id': x, 'name': x, 'field': x} for x in data[0].keys()]
    return render_page("assignments_grid.html", active_course=course, data=data, columns=columns)



@flask_app.route("/courses/<int:course_id>/assignments/update_data", methods=["POST"])
def update_assignments(course_id):
    global courses_d
    updated_data = request.get_json()  # Get the updated data sent from the client
    # Handle the updated data, e.g., update your database
    print(updated_data)
    # Return a response to the client
    return jsonify({'message': 'Data updated successfully'})




if __name__ == "__main__":
    flask_app.run(debug=True)
