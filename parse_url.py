from urllib.parse import urlparse, parse_qs, unquote

def parse_canvas_url(url,include=None):
    if url is None:
        return ''
    include = include or []
    code_lines = []
    parsed_url = urlparse(unquote(url))
    base_url = parsed_url.scheme + "://" + parsed_url.netloc
    code_lines += basic_setup(base_url)
    
    path_components = parsed_url.path.strip('/').split('/')

    # Canvas URL patterns and actions
    canvas_actions = {
        'assignments': handle_assignment,
        'modules': handle_module,
        'file': handle_file,
        'files': handle_file_folder,
        'rubrics': handle_rubric,
        'users': handle_user,
        'grades': handle_grades,
        'discussion_topics': handle_discussion,
        'announcements': handle_announcement,
        'quizzes': handle_quiz,
        'gradebook': handle_gradebook,
    }

    # TODO: handle include[] to also setup other things, like users, assignments, modules, etc.

    # Parse URL based on its structure
    if path_components[0] == 'courses':
        if len(path_components) > 1:
            course_id = path_components[1]
            code_lines += [f'course = canvas.get_course({course_id})']
            action = path_components[2] if len(path_components) > 2 else None

            if action in canvas_actions:
                code_lines += canvas_actions[action](course_id, path_components[3:], parse_qs(parsed_url.query))
            else:
                print("Unknown action:", action)
    elif path_components[0] == 'files':
        code_lines += canvas_actions['file'](path_components[1:])
    else:
        print("Invalid Canvas URL")

    code = '\n'.join(code_lines)
    return code

# Action functions for different URL types
def basic_setup(base_url):
    code_lines = []
    code_lines.append('from configparser import ConfigParser')
    code_lines.append('from canvasapi import Canvas')
    code_lines.append('def load_config(filename):')
    code_lines.append('    config = ConfigParser()')
    code_lines.append('    config.read(filename)')
    code_lines.append('    return config')
    code_lines.append('config = load_config("accounts.ini")')
    code_lines.append(f"canvas = Canvas(access_token=config['Canvas']['ACCESS_TOKEN'], base_url='{base_url}')")
    code_lines.append('courses = canvas.get_courses()')
    return code_lines

def handle_assignment(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    code_lines.append(f'assignments = course.get_assignments()')
    if len(components) == 1:
        if components[0] == 'syllabus':
            print(f"View assignments syllabus for {course_id}")
        else:
            assignment_id = components[0]
            print(f"View assignment {assignment_id} for course {course_id}")
            code_lines.append(f'assignment = course.get_assignment({assignment_id})')
            code_lines.append('if assignment.is_quiz_assignment:')
            code_lines.append('    quiz = course.get_quiz(assignment.quiz_id)')
    else:
        print(f"View all assignments for course {course_id}")
    if parameters is not None:
        if 'module_item_id' in parameters:
            code_lines.append('modules = course.get_modules()')
            code_lines.append('module_items_d = {module: module.get_module_items() for module in modules}')
            code_lines.append('def find_module_item(modules_dict, item_id):')
            code_lines.append('    for module, module_items in module_items_d.items():')
            code_lines.append('        for module_item in module_items:')
            code_lines.append("            if getattr(module_item, 'id', None) == item_id:")
            code_lines.append('                return module, module_item')
            code_lines.append('    return None, None  # Return None if the id is not found in any list')
            code_lines.append(f'module, module_item = find_module_item(module_items_d, { int(parameters['module_item_id'][0]) })')
    return code_lines

def handle_module(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    code_lines.append('modules = course.get_modules()')
    print(components)
    if len(components) == 2 and components[0] == 'items':
        print(f"View module item {components[1]} for course {course_id}")
        code_lines.append('module_items_d = {module: module.get_module_items() for module in modules}')
        code_lines.append('def find_module_item(modules_dict, item_id):')
        code_lines.append('    for module, module_items in module_items_d.items():')
        code_lines.append('        for module_item in module_items:')
        code_lines.append("            if getattr(module_item, 'id', None) == item_id:")
        code_lines.append('                return module, module_item')
        code_lines.append('    return None, None  # Return None if the id is not found in any list')
        code_lines.append(f'module, module_item = find_module_item(module_items_d, { components[1] })')
    else:
        print(f"View all modules for course {course_id}")
    return code_lines

def handle_file(components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    code_lines.append('files = course.get_files()')
    if len(components) > 0:
        file_id = components[0]
        code_lines.append(f'file = course.get_file({ file_id })')
        code_lines.append(f'folder = course.get_folder(file.folder_id)')
    return code_lines
def handle_file_folder(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    path = '/'.join(components[1:])
    print(path)
    code_lines.append(f"folder_path = course.resolve_path('{ path }')")
    code_lines.append(f'folder = list(folder_path)[-1]')
    return code_lines
def handle_rubric(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    code_lines.append('rubrics = course.get_rubrics()')
    if len(components) > 0:
        rubric_id = components[0]
        code_lines.append(f'rubric = course.get_rubric({ rubric_id })')
    return code_lines
def handle_user(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    code_lines.append('users = course.get_users()')
    if len(components) > 0:
        user_id = components[0]
        code_lines.append(f'user = course.get_user({ user_id })')
    return code_lines
def handle_quiz(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    code_lines.append('quizzes = course.get_quizzes()')
    if len(components) > 0:
        quiz_id = components[0]
        code_lines.append(f'quiz = course.get_quiz({ quiz_id })')
    return code_lines

def handle_grades(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    # TODO: handle general grades -- redirect to /gradebook
    
    if len(components) > 0:
        user_id = components[0]
        code_lines.append(f'user = course.get_user({ user_id })')
        code_lines.append(f'user_grades = course.get_user_in_a_course_level_assignment_data({ user_id })')
    return code_lines
def handle_discussion(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    return code_lines
def handle_announcement(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    return code_lines
def handle_gradebook(course_id, components, parameters=None):
    code_lines = []
    code_lines.append(f'course = canvas.get_course({course_id})')
    return code_lines


# Test URLs
urls = [
# 'https://canvas.instructure.com/courses/7675174/assignments', # works
# 'https://canvas.instructure.com/courses/7675174/assignments/40236311', # works
# 'https://canvas.instructure.com/courses/7675491/assignments/syllabus', # works
# 'https://canvas.instructure.com/courses/7675491/assignments/42244179?module_item_id=97708252', # works
# 'https://canvas.instructure.com/courses/7675174/modules', # works
# 'https://canvas.instructure.com/courses/7675491/modules/items/97807623', # works
'https://canvas.instructure.com/courses/7675491/quizzes/15527267',
# 'https://canvas.instructure.com/files/225989539/download?download_frd=1',
# 'https://canvas.instructure.com/courses/7675491/files/folder/course_image',
# 'https://canvas.instructure.com/courses/7675491/rubrics',
'https://canvas.instructure.com/courses/7675491/users', # works
'https://canvas.instructure.com/courses/7675491/users/37489575', # works
# 'https://canvas.instructure.com/courses/7675491/grades',
# 'https://canvas.instructure.com/courses/7675174/gradebook',
# 'https://canvas.instructure.com/courses/7675491/discussion_topics',
# 'https://canvas.instructure.com/courses/7675491/discussion_topics/19418385',
# 'https://canvas.instructure.com/courses/7675491/announcements',
]

# Parse and perform actions for each URL
for url in urls:
    print("\nParsing:", url)
    print(parse_canvas_url(url))
    print()
