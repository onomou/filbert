from flask import (
    Flask,
    request,
    render_template,
    redirect,
    flash,
    url_for,
    send_from_directory,
    jsonify,
    send_file,
)
from markupsafe import Markup
from canvasapi import Canvas
from datetime import datetime
import dateutil.parser
import pytz
import configparser # TODO: consider using TOML/tomlkit instead
import csv
import os
# from werkzeug.utils import secure_filename
import re
user_fields = [
    'id',
    'name',
    'short_name',
    'sortable_name',
    # 'title',
    # 'bio',
    'primary_email',
    'login_id',
    # 'time_zone',
    # 'last_login',
    # 'locale',
    # 'last_name',
    # 'first_name',
    # 'sis_user_id',
    # 'sis_import_id',
    # 'integration_id',
    # 'avatar_url',
    # 'avatar_state',
    'enrollments',
    'email',
]
profile_fields = [
    'id',
    'name',
    'short_name',
    'sortable_name',
    'avatar_url',
    'title',
    'bio',
    'primary_email',
    'login_id',
    # 'sis_user_id',
    # 'integration_id',
    'time_zone',
    'locale',
]
enrollment_fields = [
    'id',
    'user_id',
    'course_id',
    'type',
    'role',
    'enrollment_state',
]
enrollment_user_fields = [
    'id',
    'name',
    'created_at',
    'sortable_name',
    'short_name',
    'sis_user_id',
    'integration_id',
    'root_account',
    'login_id',
]
required_server_fields = ['access_token', 'base_url', 'custom_certificate']
flask_options = ['TEMP_DIR', 'LAST_SERVER']

log_filename = 'filbert.log'
config_filename = 'config.ini'
servers_filename = 'servers.ini'

def log_action(*the_strings):
    with open(log_filename, 'a', encoding='utf-8') as file:
        for string in the_strings:
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            file.write('[' + current_datetime + '] ' + string + '\n')

def load_config(filename, required_fields=[]):
    the_config = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
    the_config.write(open(filename, 'a')) # creates file if necessary
    the_config.read(filename)
    for field in required_fields:
        for section in the_config.sections():
            if field not in the_config[section]:
                the_config[section][field] = ''
    return the_config

def write_config(filename, config):
    with open(filename, 'w') as config_file:
        config.write(config_file)

log_action('start filbert')

config = load_config(config_filename, flask_options)
if 'Flask' not in config:
    config.add_section('Flask')
    write_config(config_filename, config)
    config = load_config(config_filename, flask_options)

servers = load_config(servers_filename, required_server_fields)

course_defaults = load_config('course_defaults.ini')
active_profile = config['Flask']['last_server']
if active_profile not in servers:
    active_profile = ''

# Flask section
flask_app = Flask(__name__, static_folder='static')
flask_app.static_folder = 'static'
flask_app.static_url_path = '/static'
flask_app.secret_key = 'fjeioaijcvmew908jcweio320'
flask_app.config['UPLOAD_FOLDER'] = servers.get('Flask', 'TEMP_DIR', fallback='temp') # TODO: handle missing config key
flask_app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 # maximum file upload 20MB

# Ensure the upload folder exists; create it if necessary
os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)

from util import ListConverter, format_date, rename_section, sanitize
flask_app.url_map.converters['list'] = ListConverter
flask_app.jinja_env.filters['format_date'] = format_date



@flask_app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(flask_app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon',
    )

# Canvas section
# assignments_d = {course.id:{x.id for x in course.get_assignments()} for course in courses}
# assignment_groups = {}
canvas_d = {}
'''
canvas = Canvas(BASE_URL, ACCESS_TOKEN)
courses = canvas.get_courses(include=['course_image'])
canvas_d = {'BASE_URL': BASE_URL,
            'ACCESS_TOKEN': ACCESS_TOKEN,
            'canvas': canvas,
            'courses': {x.id: {'course': x} for x in courses},
            }
for course_id in canvas_d['courses'].keys():
    canvas_d['courses'][course_id]['assignments'] = {}
    canvas_d['courses'][course_id]['assignment_groups'] = {}
    canvas_d['courses'][course_id]['quizzes'] = {}
    canvas_d['courses'][course_id]['users'] = {}
    canvas_d['courses'][course_id]['enrollments'] = {}
    canvas_d['courses'][course_id]['modules'] = {}
'''
# canvas['courses'][course_id]['assignments']
selected_course = None


# canvas helper dict functions
def ensure_canvas_valid(f):
    def wrapper(*args, **kwargs):
        if canvas_d.get('canvas') is None:
            return None
        try:
            if canvas_d.get('valid') is None:
                canvas_d['canvas'].get_current_user() # will fail if canvas url or key are invalid
                canvas_d['valid'] = True
            return f(*args, **kwargs)
        except:
            return None
    return wrapper

def ensure_course_exists(f):
    @ensure_canvas_valid
    def wrapper(*args, **kwargs):
        if len(args) == 0 or args[0] not in canvas_d['courses']:
            return None
        else:
            return f(*args, **kwargs)
    return wrapper

@ensure_canvas_valid
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

def get_courses(partial_refresh=False, refresh=False):
    global canvas_d
    if canvas_d.get('canvas') is None:
        refresh = True
    if partial_refresh:
        print('partial refresh courses')
        canvas = canvas_d['canvas'] # BUG: will throw error if canvas not valid
        courses = canvas.get_courses(include=['course_image'])
        for course in courses:
            if course.id not in canvas_d['courses']:
                canvas_d['courses'][course.id] = {'course': course}
                canvas_d['courses'][course.id]['assignments'] = {}
                canvas_d['courses'][course.id]['assignment_groups'] = {}
                canvas_d['courses'][course.id]['quizzes'] = {}
                canvas_d['courses'][course.id]['users'] = {}
                canvas_d['courses'][course.id]['enrollments'] = {}
                canvas_d['courses'][course.id]['modules'] = {}
            else:
                canvas_d['courses'][course.id]['course'] = course
    if refresh:
        print('refresh courses')
        base_url = servers.get(active_profile, 'base_url', fallback='') # TODO: handle missing config key
        access_token = servers.get(active_profile, 'access_token', fallback='-1') # TODO: handle missing config key
        if servers.get(active_profile, 'custom_certificate', fallback=None) is None or servers.get(active_profile, 'custom_certificate') in ['None', '']:
            _ = os.environ.pop('REQUESTS_CA_BUNDLE', '')
        else:
            os.environ['REQUESTS_CA_BUNDLE'] = servers.get(active_profile, 'custom_certificate')
        try:
            canvas = Canvas(base_url, access_token)
            canvas.get_current_user() # will fail if canvas url or key are invalid
            canvas_d['valid'] = True
        except:
            canvas_d['canvas'] = None
            return None
        courses = canvas.get_courses(include=['course_image'])
        # assignments_d = {course.id:{x.id for x in course.get_assignments()} for course in courses}
        # assignment_groups = {}
        canvas_d['base_url'] = base_url
        canvas_d['access_token'] = access_token
        canvas_d['canvas'] = canvas
        canvas_d['courses'] = {x.id: {'course': x} for x in courses}
        for course_id in canvas_d['courses'].keys():
            canvas_d['courses'][course_id]['assignments'] = {}
            canvas_d['courses'][course_id]['assignment_groups'] = {}
            canvas_d['courses'][course_id]['quizzes'] = {}
            canvas_d['courses'][course_id]['users'] = {}
            canvas_d['courses'][course_id]['enrollments'] = {}
            canvas_d['courses'][course_id]['modules'] = {}
    return [x['course'] for x in canvas_d['courses'].values()]

@ensure_course_exists
def get_course(course_id):
    course_id = int(course_id)
    if course_id in canvas_d['courses']:
        return canvas_d['courses'][course_id]['course']
    return None

@ensure_course_exists
def get_assignments(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['assignments'] == {} or refresh:
        print('refresh assignments: ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['assignments'] = {x.id: {'assignment': x} for x in course.get_assignments()}

        for x in [x['assignment'] for x in canvas_d['courses'][course_id]['assignments'].values()]:
            x.safe_description = Markup(x.description)
            if x.due_at is not None:
                x.due_at_local = dateutil.parser.parse(x.due_at).astimezone(pytz.timezone(course.time_zone)).strftime('%Y-%m-%d %H:%M')
                x.short_date = dateutil.parser.parse(x.due_at).astimezone(pytz.timezone(course.time_zone)).strftime('%Y-%m-%d')
    assignments = [x['assignment'] for x in canvas_d['courses'][course_id]['assignments'].values()]
    # TODO: choose sort type
    return sorted(assignments, key=lambda x: getattr(x,'due_at','') or '')

@ensure_course_exists
def get_assignment(course_id, assignment_id):
    course_id = int(course_id)
    assignment_id = int(assignment_id)
    if assignment_id not in canvas_d['courses'][course_id]['assignments']:
        print('missed assignment ' + str(assignment_id) + ' in course ' + str(course_id))
        # canvas_d['courses'][course_id]['assignments'][assignment_id] = {'assignment': course.get_assignment(assignment_id)}
        get_assignments(course_id, True)
    assignment = None
    if assignment_id in canvas_d['courses'][course_id]['assignments']:
        assignment = canvas_d['courses'][course_id]['assignments'][assignment_id]['assignment']
    return assignment
    

@ensure_course_exists
def get_assignment_groups(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['assignment_groups'] == {} or refresh:
        print('refresh assignment groups: ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['assignment_groups'] = {x.id: {'assignment_group': x} for x in course.get_assignment_groups()}
    return [x['assignment_group'] for x in canvas_d['courses'][course_id]['assignment_groups'].values()]

@ensure_course_exists
def get_modules(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['modules'] == {} or refresh:
        print('refresh modules: ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        for module in course.get_modules():
            get_module(course_id, module.id, True)
        # canvas_d['courses'][course_id]['modules'] = {x.id: {'module': x, 'module_items': {y.id: y for y in x.get_module_items()}} for x in course.get_modules()}
    return [x['module'] for x in canvas_d['courses'][course_id]['modules'].values()]

@ensure_course_exists
def get_module(course_id, module_id, refresh=False):
    course_id = int(course_id)
    module_id = int(module_id)
    if module_id not in canvas_d['courses'][course_id]['modules'] or refresh:
        print('missed module ' + str(module_id) + ' in course ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        module = course.get_module(module_id)
        canvas_d['courses'][course_id]['modules'][module_id] = {'module': module, 'module_items': {module_item.id: module_item for module_item in module.get_module_items()}}
    return canvas_d['courses'][course_id]['modules'][module_id]['module']

@ensure_course_exists
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

@ensure_course_exists
def get_module_items(course_id, module_id, refresh=False):
    course_id = int(course_id)
    module_id = int(module_id)
    if refresh:
        get_module(course_id, module_id, True)
    return canvas_d['courses'][course_id]['modules'][module_id]['module_items']

@ensure_course_exists
def get_quizzes(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['quizzes'] == {} or refresh:
        print('refresh quizzes: ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['quizzes'] = {x.id: {'quiz': x} for x in course.get_quizzes()}
    return [x['quiz'] for x in canvas_d['courses'][course_id]['quizzes'].values()]

@ensure_course_exists
def get_quiz(course_id, quiz_id, refresh=False):
    course_id = int(course_id)
    quiz_id = int(quiz_id)
    if quiz_id not in canvas_d['courses'][course_id]['quizzes'] or refresh:
        print('missed quiz ' + str(quiz_id) + ' in course ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['quizzes'][quiz_id] = {'quiz': course.get_quiz(quiz_id)}
    return canvas_d['courses'][course_id]['quizzes'][quiz_id]['quiz']

@ensure_course_exists
def get_users(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['users'] == {} or refresh:
        print('refresh users: ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['users'] = {x.id: {'user': x} for x in course.get_users()}
    return [x['user'] for x in canvas_d['courses'][course_id]['users'].values()]

@ensure_course_exists
def get_user(course_id, user_id, refresh=False):
    course_id = int(course_id)
    user_id = int(user_id)
    if user_id not in canvas_d['courses'][course_id]['users'] or refresh:
        print(f'refresh user {user_id} in {course_id}')
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['users'][user_id]['user'] = course.get_user(user_id)
    return canvas_d['courses'][course_id]['users'][user_id]['user']

@ensure_course_exists
def get_profile(course_id, user_id, refresh=False):
    course_id = int(course_id)
    user_id = int(user_id)
    user = get_user(course_id, user_id)
    if 'profile' not in canvas_d['courses'][course_id]['users'][user_id]:
        print(f'refresh profile {user_id} in {course_id}')
        try:
            response = canvas_d['courses'][course_id]['users'][user_id]['profile'] = user.get_profile()
        except:
            print(f'error for {user_id}',response)
    return canvas_d['courses'][course_id]['users'][user_id]['profile']


@ensure_course_exists
def get_enrollments(course_id, refresh=False):
    course_id = int(course_id)
    if canvas_d['courses'][course_id]['enrollments'] == {} or refresh:
        print('refresh enrollments: ' + str(course_id))
        course = canvas_d['courses'][course_id]['course']
        canvas_d['courses'][course_id]['enrollments'] = {x.id: {'enrollment': x} for x in course.get_enrollments()}
    return [x['enrollment'] for x in canvas_d['courses'][course_id]['enrollments'].values()]

# other helper functions
@ensure_course_exists
def fix_module_ordering(course_id, module_id):
    log_action(f'fix_module_ordering({course_id}, {module_id})')
    module_items = get_module_items(course_id, module_id, refresh=True).values()
    if not all(x.position == i for i, x in enumerate(module_items, 1)):
        print('reorder modules: reverse')
        for index, module_item in reversed(list(enumerate(module_items, 1))):
            if module_item.position != index:
                print(index,module_item.position)
                log_action(f"module_item.edit(module_item={{'position':{max(index,module_item.position)}}})")
                module_item.edit(module_item={'position':max(index,module_item.position)})
        print('reorder modules: forward')
        for index, module_item in enumerate(get_module_items(course_id, module_id, refresh=True).values(),1):
            if module_item.position != index:
                print(index,module_item.position)
                log_action(f"module_item.edit(module_item={{'position':{index}}})")
                module_item.edit(module_item={'position':index})

@ensure_course_exists
def get_times(course_id):
    course_id = str(course_id)
    course_times = course_defaults.getlist(course_id, 'DUE_TIMES', fallback=[])
    default_times = course_defaults.getlist('DEFAULTS', 'DUE_TIMES', fallback=[])
    shared_times = course_defaults.getlist('DEFAULTS', 'SHARED_TIMES', fallback=[])

    all_times = course_times + shared_times
    if course_times == []:
        all_times += default_times
    return sorted(list(set(all_times)))
    if course_id in default_times:
        return default_times[course_id] + default_times['shared']
    else:
        return default_times['default'] + default_times['shared']
    
@ensure_course_exists
def get_submission_types(course_id):
    course_id = str(course_id)
    submission_types = course_defaults.getlist(course_id, 'SUBMISSION_TYPES', fallback=[])
    return submission_types
    
# reload_assignments()
# _ = get_assignments()

# Template context globals
# used in courses_sidebar.html to list courses
# @flask_app.template_global()
# def all_courses():
#     return 

@flask_app.context_processor
def inject_globals():
    courses = get_courses()
    if courses is None:
        courses = []
    else:
        courses = sorted(courses, key=lambda x: x.name)
        courses.sort(key=lambda x: getattr(x, 'start_at_date', datetime.now().astimezone()), reverse=True)
    return {
        'today': datetime.today().astimezone(),
        'courses': courses,
        'base_url': canvas_d.get('base_url'),
    }

def no_course_redirect(f):
    def wrapper(*args, **kwargs):
        if len(args) == 0 or args[0] not in canvas_d['courses']:
            flash('Course not found')
            return redirect(url_for('settings'))
        else:
            return f(*args, **kwargs)
    return wrapper

# Routes section
@flask_app.route('/', methods=['GET', 'POST'])
def index():
    if not canvas_d.get('valid'):
        flash('Your server information is invalid. Ensure your base_url and access_token are correct.')
        flash('Make sure your server is reachable and that its certificate is valid.')
        # raise Exception()
        return redirect(url_for('settings'))
    return render_template(
        'index.html',
        action='assignments',
    )


@flask_app.route('/refresh', methods=['GET'])
def refresh_everything():
    reload_assignments()
    flash('Reloaded everything')
    return redirect(request.referrer)


@flask_app.route('/example')
def example():
    return render_template(
        'example.html',
    )


@flask_app.route('/log')
def log_page():
    the_log = ''
    with open(log_filename) as logfile:
        the_log = logfile.read().splitlines()
    return render_template(
        'log.html',
        logfile=the_log,
        action='assignments',
    )

@flask_app.route('/log/clear')
def clear_log():
    with open(log_filename, 'w') as logfile:
        logfile.write('')
    log_action('log cleared')
    return redirect(request.referrer)

@flask_app.route('/settings', strict_slashes=False)
def settings():
    # my_config = config
    return render_template(
        'settings.html',
        active_profile=active_profile,
        config=servers,
        required_fields=required_server_fields,
        action='assignments',
    )

@flask_app.route('/update_settings', methods=['POST'])
def update_settings():
    global servers, active_profile
    # Update settings based on the form data
    active_profile = request.form.get('section-selection')
    if active_profile not in servers:
        active_profile = request.form.get('section-name')
        servers.add_section(active_profile)
        for field in required_server_fields:
            servers.set(active_profile, field, '')
    for key in request.form:
        if key not in ['section-selection', 'section-name']:
            if request.form.get('section-name') != active_profile:
                # section has been renamed
                new_section_name = request.form.get('section-name')
                rename_section(servers, active_profile, new_section_name)
                # system_config._sections[new_section_name] = system_config._sections.pop(active_profile)
                active_profile = new_section_name
            servers[active_profile][key] = request.form[key]

    # Save the updated settings
    write_config(servers_filename, servers) # TODO: only write if changed
    servers = load_config(servers_filename, required_server_fields)
    _ = canvas_d.pop('valid', None)
    result = get_courses(refresh=True)
    if result is None:
        flash('Your server information is invalid. Ensure your base_url and access_token are correct.')
        flash('Make sure your server is reachable and that its certificate is valid.')
    else:
        config['Flask']['last_server'] = active_profile
        write_config(config_filename, config)
    return redirect(request.referrer)


@flask_app.route('/delete_profile', methods=['POST'])
def delete_profile():
    profile_name = request.form.get('section-selection')
    if profile_name in servers:
        log_action(f'deleted profile {profile_name} that had values {[(key, val) for key, val in servers[profile_name].items()]}')
        servers.remove_section(profile_name)
        write_config('my_config.ini', servers)
        flash('Profile '+ profile_name +' deleted!')
    else:
        flash('Profile '+ profile_name +' does not exist!')
    return redirect(request.referrer)


@flask_app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'message': 'no file posted'})
    file = request.files['file']
    if  file.filename == '':
        return jsonify({'message': 'no file posted'})
    filename = sanitize(file.filename)
    the_filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
    # print(the_filepath)
    # file.save(the_filepath)
    file.save(the_filepath)
    return jsonify({ 'location' : url_for('temp_image', filename=filename) })


@flask_app.route('/temp_image/<filename>')
def temp_image(filename):
    the_filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
    return send_file(the_filepath, mimetype='image/png')


@flask_app.route('/courses/<int:course_id>/settings', methods=['GET'])
def course_settings(course_id=None):
    if course_id is None:
        course = None
        # course_defaults = {} # TODO
    else:
        course = get_course(course_id)
        # course_defaults = course_defaults[str(course_id)]
    return render_template(
        'course_settings.html',
        active_course=course,
        # options=list(course_defaults.keys()),
        action='settings',
        link_url=make_url(course_id, 'settings'),
    )


@flask_app.route('/courses/<int:course_id>/users/data')
def users_data(course_id=None):
    if course_id is None:
        return jsonify({x: '' for x in user_fields})
    
    users = get_users(course_id)
    rows = []#[{**{x: getattr(user,x,'') for x in user_fields}, **{'profile.'+x:}} for user in users]
    for user in users:
        user_data = {x: getattr(user,x,'') for x in user_fields}
        # user_profile = user.get_profile()
        user_profile = get_profile(course_id, user.id)
        profile_data = {'profile_'+x: user_profile.get(x,'') for x in profile_fields}
        rows.append(user_data | profile_data)
    columns = [{'id': x, 'name': x, 'field': x} for x in rows[0].keys()]
    response = jsonify({'rows': rows, 'columns': columns})
    # raise Exception
    return response


def make_url(course_id, action, id=None): # options = {'action': {}, 'id': #}
    url = servers.get(active_profile, 'base_url') + '/courses/' + str(course_id)
    o = [
        'announcements',
        'discussion_topics',
        'grades',
        'users',
        'wiki',
        'files',
        'outcomes',
        'rubrics',
        'quizzes',
        'modules',
        'collaborations',
        'settings',
        'assignments',
        'syllabus', # should follow assignments
    ]
    url += '/' + str(action)
    if id is not None:
        url += '/' + str(id)
    return url

@flask_app.route('/courses/<int:course_id>/users', strict_slashes=False)
def users_page(course_id=None):
    if course_id is None:
        course = None
        users = None
    else:
        course = get_course(course_id)
        users = get_users(course_id)
    return render_template(
        'table_page.html',
        active_course = course,
        users=users,
        data_name='users_data',
        action='users',
        link_url=make_url(course_id, 'users'),
    )

@flask_app.route('/courses/<int:course_id>/users/<int:user_id>', strict_slashes=False)
def user_details(course_id=None, user_id=None):
    if course_id is None:
        course = None
        users = None
        active_user = None
    else:
        course = get_course(course_id)
        if user_id is None:
            users = None
            active_user = None
        else:
            users = get_users(course_id)
            active_user = get_user(course_id, user_id)
    return render_template(
        'table_page.html',
        active_course = course,
        users=users,
        active_user=active_user,
        action='users',
        link_url=make_url(course_id, 'users', user_id),
    )

@flask_app.route('/courses/<int:course_id>/users/refresh', strict_slashes=False)
def refresh_users(course_id=None):
    _ = get_users(course_id, refresh=True)
    return redirect(request.referrer)

@flask_app.route('/courses/<int:course_id>/enrollments/data')
def enrollments_data(course_id=None):
    if course_id is None:
        return jsonify({x: '' for x in enrollment_fields + enrollment_user_fields})
    
    users = get_users(course_id)
    enrollments = get_enrollments(course_id)
    rows = []
    for enrollment in enrollments:
        enrollment_data = {x: getattr(enrollment,x,'') for x in enrollment_fields}
        user_profile = enrollment.user
        enrollment_user_data = {'enrollment_user_'+x: user_profile.get(x,'') for x in enrollment_user_fields}
        rows.append(enrollment_data | enrollment_user_data)
    columns = [{'id': x, 'name': x, 'field': x} for x in rows[0].keys()]
    response = jsonify({'rows': rows, 'columns': columns})
    # raise Exception
    return response

@flask_app.route('/courses/<int:course_id>/enrollments', strict_slashes=False)
def enrollments_page(course_id=None):
    if course_id is None:
        course = None
        users = None
    else:
        course = get_course(course_id)
        users = get_users(course_id)
    return render_template(
        'table_page.html',
        active_course = course,
        users=users,
        data_name='enrollments_data',
        action='enrollments',
        link_url=make_url(course_id, 'enrollments'),
    )

@flask_app.route('/courses/<int:course_id>/enrollments/refresh', strict_slashes=False)
def refresh_enrollments(course_id=None):
    _ = get_enrollments(course_id, refresh=True)
    return redirect(request.referrer)

@flask_app.route('/parse_form/', methods=['GET'])
def parse_url_form():
    request_url = request.args.get('url') or None
    return redirect(url_for('parse_url', url=request_url))

@flask_app.route('/parse_url', methods=['GET'], strict_slashes=False)
@flask_app.route('/parse_url/<path:url>', methods=['GET'])
def parse_url(url=None):
    from parse_url import parse_canvas_url
    if url is None:
        url = servers.get(active_profile, 'base_url')
    details = parse_canvas_url(url)
    course = get_course(details['course_id'])
    path = request.root_url[:-1] + details['local_path']
    return render_template(
        'parse_url.html',
        url=url,
        code=details['code'],
        local_link=path,
        active_course=course,
        assignment=None,
        action='assignments',
    )

@flask_app.route('/courses', methods=['GET'], strict_slashes=False)
def courses_page():
    return redirect(url_for('index'))


@no_course_redirect
@flask_app.route('/courses/<int:course_id>/', methods=['GET'])
def course_page(course_id):
    print(get_course(course_id))
    # if get_course(course_id) is None:
    #     return redirect(url_for('courses_page'))
    return redirect(url_for('new_assignment', course_id=course_id)) # TODO: consider implementing course front page view


@flask_app.route('/courses/<int:course_id>/<action>', methods=['GET'])
def course_action(course_id, action='assignments'):
    match action:
        case 'assignments':
            return redirect(url_for('assignments_page', course_id=course_id))
        case 'assignments_list':
            return redirect(url_for('assignments_list', course_id=course_id))
        case 'list_quiz':
            return redirect(url_for('quiz_page', course_id=course_id))
        case 'assignments_bulk':
            return redirect(url_for('assignments_bulk', course_id=course_id))
        # case 'quiz_question_details':
        #     return redirect(url_for('quiz_question_details', course_id=course_id)) # TODO: handle quiz_id and question_id
        case 'users':
            return redirect(url_for('users_page', course_id=course_id))
        case _ :
            flash('Invalid URL')
            flash(request.url)
            return redirect(url_for('course_page', course_id=course_id))

'''
# TODO: delete this
@flask_app.route("/courses/<int:course_id>/assignment_default", methods=["GET"])
def list_assignments(course_id):
    course = get_course(course_id)
    assignments = get_assignments(course_id)
    assignment_groups = course.get_assignment_groups()
    modules = course.get_modules()
    return render_template(
        "assignment.html",
        active_course=course,
        assignment=None,
        assignments=assignments,
        assignment_groups=assignment_groups,
        modules=modules,
        action="assignments",
    )
'''

@flask_app.route('/courses/refresh', methods=['GET'])
def refresh_courses():
    _ = get_courses(partial_refresh=True)
    return redirect(request.referrer)

@flask_app.route('/courses/<int:course_id>/assignments/refresh', methods=['GET'])
def refresh_assignments(course_id):
    _ = get_assignments(course_id, True)
    _ = get_modules(course_id, True)
    _ = get_assignment_groups(course_id, True)
    return redirect(request.referrer)

@flask_app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/delete', methods=['POST'])
def delete_assignment(course_id, assignment_id):
    assignment = get_assignment(course_id, assignment_id)
    log_action(f'delete_assignment({course_id}, {assignment_id})')
    log_action(f'assignment.delete()')
    result = assignment.delete()
    flash('Deleted assignment ' + str(assignment_id))
    refresh_assignments(course_id)
    return redirect(url_for('assignments_page', course_id=course_id))


# call with assignment_id=0 to create new
@flask_app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/update', methods=['POST'])
def update_assignment(course_id, assignment_id=0):
    log_action(f'called update_assignment(course_id={course_id}, assignment_id={assignment_id})')
    course = get_course(course_id)
    fields = ['name', 'description', 'points_possible', 'due_at', 'published', 'assignment_group_id']
    response = {x: request.form.get(x) for x in fields}
    response['description'] = response['description'].replace('\r\n', '\n')

    # handle image uploads in description
    # if f'<img src="../../../temp_image/mceclip0.png">' in response['description']:
    pattern = r'<img src="(.+?temp_image/)(.+?)">'
    matches = re.findall(pattern, response['description'])
    for match in matches:
        filename = match[1]
        the_filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
        # upload file to canvas
        result = course.upload(the_filepath, parent_folder_path='Uploaded Media', on_duplicate='rename')
        if result[0] is True:
            # replace local path with canvas path
            canvas_file = result[1]
            # preview_url looks like '/courses/{course_id}/files/{file_id}/file_preview?annotate=0&etc...
            link_string = f'<img src="{canvas_file['preview_url'].split('?')[0].replace('file_preview','preview')}" alt="{canvas_file['display_name']}" />'
            response['description'] = re.sub(pattern, link_string, response['description'], count=1)
            

    # raise Exception

    response['published'] = bool(response['published'])
    response['submission_types'] = request.form.getlist('submission_types') or ['none']

    if 'external_tool' in response['submission_types']:
        response['external_tool_tag_attributes'] = {'url': request.form.get('url'), 'new_tab': True}
    
    # handle due_at separately
    due_at_text = request.form.get('due_at')
    try:
        due_at = pytz.timezone(course.time_zone).localize(dateutil.parser.parse(due_at_text)).astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    except:
        due_at = None
    response['due_at'] = due_at

    # TODO: insert latex equations eg. https://canvas.instructure.com/equation_images/4n-1?scale=1

    # handle file attachment
    # raise(Exception)
    file_div = 'assignment-attachment'
    if file_div in request.files:
        print('file attached to POST')
        file = request.files[file_div]
        if file.filename == '':
            # no file attached
            print('no file selected')
        else:
            # filename = secure_filename(file.filename)
            # https://stackoverflow.com/a/71199182 -- of course I trust the regex
            filename = sanitize(file.filename)
            print('filename: ' + filename)
            the_filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
            # print(the_filepath)
            # file.save(the_filepath)
            file.save(the_filepath)
            # print(url_for('download_file', name=filename))
            result = course.upload(the_filepath, parent_folder_path='Uploaded Media', on_duplicate='rename')
            if result[0] is True:
                canvas_file = result[1]
                print('uploaded file ' + canvas_file['display_name'])
                response['description'] += '<p><a class="instructure_file_link instructure_scribd_file auto_open"'\
                    + ' title="' + canvas_file['display_name'] + '"'\
                    + ' href="' + servers.get("Canvas", "base_url") + '/courses/' + str(course.id) + '/files/' + str(canvas_file['id'])\
                    + '?wrap=1 target="_blank" rel="noopener" data-canvas-previewable="false">'\
                    + canvas_file['display_name'] + '</a></p>'
                    # data-api-endpoint="https://canvas.instructure.com/api/v1/courses/7675174/files/228895639"\
                    #     data-api-returntype="File">\
    
    diff_message = ''
    if assignment_id == 0:
        # create new assignment
        log_action(f'assignment = course.create_assignment(assignment={response})')
        assignment = course.create_assignment(assignment=response)
        flash('<em>Created new assignment</em>')
        flash('<h2><a href="' + assignment.html_url + '" target="_blank" rel="noopener noreferrer">🔗 ' + assignment.name + '</a></h2>')
        flash(assignment.description)
    else:
        # update existing assignment
        changes = {}
        assignment = get_assignment(course_id, assignment_id)
        response['external_tool_tag_attributes'] = getattr(assignment,'external_tool_tag_attributes',{}) | response.get('external_tool_tag_attributes', {})
        if len(response['external_tool_tag_attributes']) == 0:
            _ = response.pop('external_tool_tag_attributes', None)
        # get differences between original and new data
        for key, val in response.items():
            if str(getattr(assignment,key,None)) != str(val):
                changes[key] = {'old': getattr(assignment,key,None), 'new': val} # TODO: handle changes in sub-attributes, like external_tool_tag_attributes
        if changes == {}:
            diff_message += 'No changes to assignment'
        else:
            diff_message = '<h3>Assignment Differences</h3>'
            diff_message += '<table class="diff-table" id="assignment-diff">'
            # diff_message += '<tr><th colspan="3">Assignment Differences</th></tr>'
            diff_message += '<tr><th>Field</th><th>Old Value</th><th>New Value</th></tr>'
            changes_dict = {key: val['new'] for key, val in changes.items()}
            old_values = {key: val['old'] for key, val in changes.items()}
            log_action(f'assignment old values {old_values})')
            log_action(f'assignment.edit(assignment={changes_dict})')
            assignment.edit(assignment=changes_dict)
            for field, change in changes.items():
                # diff_message += '<em>' + field + '</em>: ' + str(change)
                diff_message += '<tr>'
                diff_message += '<td>' + field + '</td>'
                diff_message += '<td>' + str(change['old']) + '</td>'
                diff_message += '<td>' + str(change['new']) + '</td>'
                diff_message += '</tr>'
            diff_message += '</table>'
        diff_message += '\n'
        flash('<h2><a href="' + assignment.html_url + '" target="_blank" rel="noopener noreferrer">🔗 ' + assignment.name + '</a></h2>')
        flash(diff_message)
    
    if assignment is not None:
        # add assignment to selected modules
        assignment_module_ids = get_assignment_module_ids(assignment.course_id, assignment.id)
        selected_module_ids = [int(x) for x in request.form.getlist('modules')]
        # TODO: split selected_module_ids into insertions and deletions, and handle each
        module_insertions = set([x for x in selected_module_ids if x not in assignment_module_ids])
        print('will add to ' + str(module_insertions))
        module_deletions = set([x for x in assignment_module_ids if x not in selected_module_ids])
        print('will delete from ' + str(module_deletions))
        selected_modules = []
        created_module_items = []
        print(selected_module_ids)
        for module_id in module_insertions:
            try:
                module = get_module(course_id, module_id)
                selected_modules.append(module)
                print(module.name)
                fix_module_ordering(course_id, module_id)
                item_details = {
                    'type': 'assignment',
                    'content_id': assignment.id,
                    'position': module.items_count+1,
                }
                log_action(f'module_item = module.create_module_item(module_item={item_details})')
                module_item = module.create_module_item(module_item=item_details)
                created_module_items.append(module)
            except:
                print('failed to create module item')
        deleted_module_items = []
        for module_id in module_deletions:
            try:
                module = get_module(course_id, module_id)
                module_items = get_module_items(course_id, module_id)
                for module_item in module_items.values():
                    print(str(getattr(module_item,'content_id',0)) + ' vs ' + str(module_id) + ' is ' + str(getattr(module_item,'content_id',0) == module_id))
                    if getattr(module_item,'content_id',0) == assignment.id:
                        log_action(f'module_item.delete(): {module_item}')
                        module_item.delete()
                        deleted_module_items.append(module.name)
                fix_module_ordering(course_id, module_id)
            except:
                print('failed to delete module item')
        if len(created_module_items) + len(deleted_module_items) > 0:
            # flash('<h3>Modules</h3>')
            # flash('<b>Added to:</b>')
            # flash(", ".join(module.name for module in created_module_items))
            # flash('<b>Removed from:</b>')
            # flash(','.join(module_name for module_name in deleted_module_items))

            diff_message = ''
            diff_message += '<table class="diff-table" id="modules-diff">'
            diff_message += '<tr><th colspan="2">Modules</th></tr>'
            diff_message += '<tr><th>Added To</th><th>Removed From</th></tr>'
            diff_message += '<tr><td>' + '\n'.join(module.name for module in created_module_items) + '</td><td>' + '\n'.join(module_name for module_name in deleted_module_items) + '</tr>'
            diff_message += '</table>'
            flash(diff_message)
        else:
            flash('<em>Modules unchanged</em>')

        return redirect(url_for('assignments_page', course_id=course_id, assignment_id=assignment.id))
    else:
        flash('This feature is not yet implemented.')
        return redirect(request.referrer)

def get_assignment_details(course_id, assignment_id=None):
    the_details = {}
    course = get_course(course_id)
    if course is None:
        return None
    if assignment_id is None:
        # creating new assignment
        assignment = None
    else:
        assignment = get_assignment(course_id, assignment_id)
    
    assignments = get_assignments(course_id)
    assignment_groups = get_assignment_groups(course_id)
    modules = get_modules(course_id)
    
    groups_count = int(course_defaults.get('DEFAULT', 'MIN_LINES', fallback=5))
    
    assignment_modules = get_assignment_module_ids(course_id, assignment_id) #
    default_times = get_times(course_id)
    default_submission_types = get_submission_types(course_id)
    # print('check this out: ' + str(default_times))
    # print(assignment.description)
    submission_types = ['discussion_topic', 'online_quiz', 'on_paper', #'none',
                        'external_tool', 'online_text_entry', 
                        'online_url', 'online_upload', 'media_recording', 
                        'student_annotation']

    the_details['active_course'] = course
    the_details['assignment'] = assignment
    the_details['assignments'] = assignments
    the_details['assignment_groups'] = assignment_groups
    the_details['modules'] = modules
    the_details['assignment_modules'] = assignment_modules
    the_details['groups_count'] = groups_count
    the_details['default_times'] = default_times
    the_details['default_submission_types'] = default_submission_types
    the_details['submission_types'] = submission_types
    the_details['link_url'] = getattr(assignment,'html_url',make_url(course_id,'assignments'))
    return the_details

@flask_app.route('/courses/<int:course_id>/render_topbar')
@flask_app.route('/courses/<int:course_id>/render_topbar/<path:url>')
def render_topbar(course_id, url=None):
    active_course = get_course(course_id)
    return render_template(
        'topbar.html',
        active_course=active_course,
        link_url=url,
    )

@flask_app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/silent')
def push_page(course_id, assignment_id):
    the_details = get_assignment_details(course_id, assignment_id)
    return render_template(
        'assignment_details.html',
        **the_details
    )

@flask_app.route('/courses/<int:course_id>/assignments/new', methods=['GET'], strict_slashes=False)
def new_assignment(course_id):
    the_details = get_assignment_details(course_id)
    if the_details is None:
        flash('Course not found')
        return redirect(url_for('index'))
    return render_template(
        'assignments.html',
        **the_details,
        action='assignments',
    )

@flask_app.route('/courses/<int:course_id>/assignments', methods=['GET'], strict_slashes=False)
@flask_app.route('/courses/<int:course_id>/assignments/<int:assignment_id>', methods=['GET'])
def assignments_page(course_id, assignment_id=None):
    the_details = get_assignment_details(course_id, assignment_id)
    if the_details is None:
        return redirect(url_for('index'))
    elif assignment_id is None:
        return redirect(url_for('new_assignment', course_id=course_id))
    elif the_details['assignment'] is None:
        flash(f'Assignment {assignment_id} does not exist')
        return redirect(url_for('new_assignment', course_id=course_id))
    return render_template(
        'assignments.html',
        **the_details,
        action='assignments',
    )

@flask_app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/raw', methods=['GET'])
def assignments_raw(course_id, assignment_id):
    the_details = get_assignment_details(course_id, assignment_id)
    if the_details is None:
        return redirect(url_for('index'))
    elif the_details['assignment'] is None:
        flash(f'Assignment {assignment_id} does not exist')
        return redirect(url_for('new_assignment', course_id=course_id))
    return render_template(
        'assignment_raw.html',
        **the_details,
        assignment_raw=the_details['assignment'].__dict__,#{x: getattr(the_details['assignment'], x) for x in dir(the_details['assignment']) if not x.startswith('_')},
        action='assignments',
    )

@flask_app.route('/courses/<int:course_id>/assignments/all')
@flask_app.route('/courses/<int:course_id>/assignments/list')
def assignments_list(course_id):
    course = get_course(course_id)
    assignments = get_assignments(course_id)
    
    return render_template(
        'assignments_list.html',
        assignments=assignments,
        active_course=course,
        action='assignments_list',
        link_url=make_url(course_id, 'assignments'),
    )

@flask_app.route('/courses/<int:course_id>/assignments_bulk/intersect/')
@flask_app.route('/courses/<int:course_id>/assignments_bulk/intersect/<list:assignment_ids>', methods=['GET'])
def get_selected_assignments(course_id, assignment_ids=None):
    assignment_ids = assignment_ids or []
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


@flask_app.route('/courses/<int:course_id>/assignments_bulk/update/<list:assignment_ids>', methods=['POST'])
def assignments_bulk_update(course_id,assignment_ids=None):
    assignment_ids = assignment_ids or []
    # TODO: implement this
    return redirect(request.referrer)


@flask_app.route('/courses/<int:course_id>/assignments_bulk/delete/<list:assignment_ids>', methods=['POST'])
def assignments_bulk_delete(course_id,assignment_ids=None):
    assignment_ids = assignment_ids or []
    # TODO: implement this
    return redirect(request.referrer)


@flask_app.route('/courses/<int:course_id>/assignments_bulk', methods=['GET'], strict_slashes=False)
@flask_app.route('/courses/<int:course_id>/assignments_bulk/<list:assignment_ids>', methods=['GET'])
def assignments_bulk(course_id,assignment_ids=None):
    assignment_ids = assignment_ids or []
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

    return render_template(
        'assignments_bulk.html',
        active_course=course,
        assignments=assignments,
        selected_assignments=selected_assignments,
        selected_assignment_ids=assignment_ids,
        quiz=None,
        modules=modules,
        action='assignments_bulk',
        link_url=make_url(course_id, 'assignments'),
    )


@flask_app.route('/courses/<int:course_id>/quizzes', methods=['GET', 'POST'])
def quiz_page(course_id):
    course = get_course(course_id)
    modules = get_modules(course_id)
    quizzes = get_quizzes(course_id)

    if request.method == 'POST':
        return redirect(request.referrer)
    return render_template(
        'quiz_details.html',
        active_course=course,
        quiz=None,
        quizzes=quizzes,
        modules=modules,
        action='list_quiz',
        link_url=make_url(course_id, 'quizzes'),
    )


@flask_app.route('/courses/<int:course_id>/quizzes/<quiz_id>', methods=['GET', 'POST'])
def quiz_details(course_id, quiz_id):
    course = get_course(course_id)
    modules = get_modules(course_id)
    quizzes = get_quizzes(course_id)
    quiz = get_quiz(course_id, quiz_id)
    quiz_questions = quiz.get_questions()

    if request.method == 'POST':
        return redirect(request.referrer)
    return render_template(
        'quiz_details.html',
        active_course=course,
        quiz=quiz,
        quiz_questions=quiz_questions,
        quizzes=quizzes,
        modules=modules,
        action='list_quiz',
        link_url=make_url(course_id, 'quizzes', quiz_id),
    )


@flask_app.route(
    '/courses/<int:course_id>/quizzes/<quiz_id>/question/<question_id>', methods=['GET', 'POST']
)
def quiz_question_details(course_id, quiz_id, question_id):
    course = get_course(course_id)
    modules = get_modules(course_id)
    quizzes = get_quizzes(course_id)
    quiz = get_quiz(course_id, quiz_id)
    quiz_questions = quiz.get_questions()
    quiz_question = quiz.get_question(question_id)

    if request.method == 'POST':
        log_action(f'quiz_question_details({course_id}, {quiz_id}, {question_id})')
        # code to update the quiz question
        question_name = request.form.get('question_name')
        question_text = request.form.get('question_text')
        position = request.form.get('position')
        points_possible = request.form.get('points_possible')
        details = {
            'quiz_id': quiz.id,
            'id': question_id,
            'question_text': question_text,
            'question_name': question_name,
            'position': position,
            'points_possible': points_possible,
        }
        log_action(f'question = quiz_question.edit({details})')
        question = quiz_question.edit(details)

        flash('Quiz question updated!')
        return redirect(request.referrer)
    return render_template(
        'quiz_question_details.html',
        active_course=course,
        quiz=quiz,
        quiz_questions=quiz_questions,
        quiz_question=quiz_question,
        quizzes=quizzes,
        modules=modules,
        action='quiz_question_details',
        link_url=make_url(course_id, 'quizzes', quiz_id),
    )


@flask_app.route(
    '/courses/<int:course_id>/quizzes/<quiz_id>/question/<question_id>/download', methods=['POST']
)
def quiz_question_download(course_id, quiz_id, question_id):
    question_id = int(question_id)
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
    '/courses/<int:course_id>/quizzes/<quiz_id>/question/<question_id>/upload', methods=['POST']
)
def quiz_question_upload(course_id, quiz_id, question_id):
    question_id = int(question_id)
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
    old_message = []
    new_message = []
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
                old_message.append(str(o_data))
                new_message.append(str(n_data))
                n_data.update([('question_id', original['question_id']), ('user_id', original['user_id']), ('attempt', original['attempt'])])
                new_data.append(dict(n_data))
    flash_message = '<table><tr>' + ''.join(f'<td>{x}</td><td>{y}</td>' for x, y in zip(old_message, new_message)) + '</tr></table>'
    
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
    course = get_course(course_id)
    assignments = get_assignments(course_id)
    data = [{'id': x.id, 'name': x.name, 'points': x.points_possible, 'published': x.published} for x in assignments]
    return data


@flask_app.route('/courses/<int:course_id>/assignments/grid', methods=['GET', 'POST'])
def assignments_grid(course_id):
    course = get_course(course_id)
    assignments = get_assignments(course_id)
    data = [{'id': x.id, 'name': x.name, 'points_possible': x.points_possible, 'published': x.published} for x in assignments]
    columns = [{'id': x, 'name': x, 'field': x} for x in data[0].keys()]
    return render_template(
        'assignments_grid.html', 
        active_course=course, 
        data=data, 
        columns=columns,
        action='grid',
        link_url=make_url(course_id, 'assignments'),
    )


@flask_app.route('/courses/<int:course_id>/assignments/update_data', methods=['POST'])
def update_assignments(course_id):
    updated_data = request.get_json()  # Get the updated data sent from the client
    # Handle the updated data, e.g., update your database
    print(updated_data)
    # Return a response to the client
    return jsonify({'message': 'Data updated successfully'})


_ = get_courses(refresh=True)
if __name__ == '__main__':
    flask_app.run(debug=True)
