# https://exploreflask.com/en/latest/views.html#custom-converters
from werkzeug.routing import BaseConverter
from datetime import datetime
from markupsafe import Markup

class ListConverter(BaseConverter):

    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(str(value) for value in values)

# Date formatter
def format_date(date_string):
    if date_string is None:
        return 'None'
    date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
    formatted_date = date_obj.strftime('%Y-%m-%d %I:%M %p')
    return Markup(formatted_date)  # Use Markup to avoid HTML escaping
