# Filbert

This is a Flask app for quickly adding and changing information in Canvas. The primary focus is on managing assignments.

## Features

* Create new assignment, and add it to one or more modules
* Edit existing assignments, adding to or removing from modules
* Duplicate existing assignments, and copy across courses
* List all assignments and details on one page
* List all users and enrollments
* Generate Python code for most URLs in Canvas
* List quiz questions, download user responses by question, and upload quiz question grades with comments (all in CSV format; editing online not available yet)

## Getting Started

1. Clone this repository
1. Install requirements
`pip install -r requirements `
1. Generate an API token (go to https://yourinstitution.instructure.com/profile/settings and generate a new token)
1. Edit `config.ini` and modify your server information
    ```ini
    # example -- lines beginning with # are comments
    BASE_URL = https://canvas.instructure.com # Free for Teachers site
    ACCESS_TOKEN = 7~Px2KcYbRjo815qv7mt4W6HNuZgB3lasfIiDFUzSeA8XTGhM0nQrVyLpOxdECJ4wK # fake API KEY; use your own
    ```
1. You can include a section for each course by ID to specify defaults, such as submission_type and hints for due_at.
    ```ini
    #Algebra 98
    [7654321]
    DUE_TIMES = 08:28,9:08 # shows these options in the date picker, so you can select beginning/end of class due time
    SUBMISSION_TYPES = on_paper,online_upload # selects these options for assignment submission types
    ```
1. Run the script
`py script.py`
1. Open the Flask site, which defaults to http://localhost:5000/

## Screenshots

![Assignment Editing](/docs/images/assignment.png)

![Assignment Editing - Change Report](/docs/images/assignment_changes.png)

![Generate Code](/docs/images/setup_code.png)

![Other Options](/docs/images/other_options.png)

## Future

 - [ ] Bulk add/edit assignments
 - [ ] Bulk add/edit quiz questions
 - [ ] Add multiple due dates for assignments
 - [ ] Insert equations in assignment descriptions
 - [ ] Handle multiple users
 - [ ] OAuth2 authentication
 - [ ] Local config file support
 - [ ] Config file editor
 - [ ] Log file configuration

## Notes

Every `PUT` call to Canvas is logged to `log.txt` in the base directory. If you accidentally change an assignment's details, the old values are also logged.

This project has been my way of learning Python, how to use libraries and APIs, HTML/CSS/JS, web servers, etc. The code is improving, but still has room to grow. Several functions are incomplete. However, I use this nearly every day to post and edit actual assignments for my students, so I would consider assignment editing to be mature.

All development has been against the Canvas Free for Teachers site with a regular Teacher account.

You can run this on [PythonAnywhere](https://www.pythonanywhere.com/) with no modification. **Be sure to enable Password protection!!!** Clone the repo to somewhere like `/usr/<your user name>/filbert`. Edit your `_wsgi.py` file like this:

```python
import sys
import script

# add your project directory to the sys.path
project_home = '/usr/<your user name>/filbert'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

application = script.flask_app
```
