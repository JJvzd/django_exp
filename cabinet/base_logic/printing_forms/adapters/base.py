import os
from uuid import uuid4

from settings.settings import BASE_DIR

PATH_TEMP = os.path.join(BASE_DIR, 'temp')


def get_temp_path(extension):
    if not os.path.exists(PATH_TEMP):
        os.mkdir(PATH_TEMP)

    return os.path.join(PATH_TEMP, '%s%s' % (uuid4(), extension))


class BasePrintFormGenerator:

    def __init__(self, *args, **kwargs):
        self.template = None
        self.data = None

    def set_template(self, new_template):
        self.template = new_template

    def set_data(self, new_data):
        self.data = new_data

    def update_data_values(self, key, value):
        self.data['values'][key] = value
