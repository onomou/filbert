# https://exploreflask.com/en/latest/views.html#custom-converters
from werkzeug.routing import BaseConverter
from datetime import datetime
import dateutil.parser
import pytz
from markupsafe import Markup
import re

class ListConverter(BaseConverter):

    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(str(value) for value in values)

# Date formatter
def format_date(date_obj, time_zone=None):
    if date_obj is None:
        return 'None'
    if time_zone is not None:
        # return dateutil.parser.parse(date_string).astimezone(pytz.timezone(time_zone)).strftime('%Y-%m-%d %H:%M')
        date_obj = date_obj.astimezone(pytz.timezone(time_zone))
        
    # date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
    # formatted_date = date_obj.strftime('%Y-%m-%d %I:%M %p')
    formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
    return Markup(formatted_date)  # Use Markup to avoid HTML escaping

def short_date(date_obj, time_zone=None):
    if date_obj is None:
        return 'None'
    if time_zone is not None:
        date_obj = date_obj.astimezone(pytz.timezone(time_zone))
    # date_obj = datetime.strptime(date_obj, '%Y-%m-%dT%H:%M:%SZ')
    formatted_date = date_obj.strftime('%Y-%m-%d')
    return Markup(formatted_date)  # Use Markup to avoid HTML escaping

def rename_section(config, old_section, new_section):
    # Create a new section with the desired name
    config.add_section(new_section)

    # Copy items from the old section to the new one
    for (name, value) in config.items(old_section):
        config.set(new_section, name, value)

    # Remove the old section
    config.remove_section(old_section)


windows_badnames = (
    'CON',
    'AUX',
    'COM1',
    'COM2',
    'COM3',
    'COM4',
    'LPT1',
    'LPT2',
    'LPT3',
    'PRN',
    'NUL',
)
def sanitize(filename):
    clean_name = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", '-', filename)
    if clean_name in windows_badnames:
        clean_name = clean_name + '_'
    return clean_name