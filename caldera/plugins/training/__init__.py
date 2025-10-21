import os
from base64 import b32encode

from plugins.training.app.c_flag import Flag

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


def calculate_code(self):
    if self.started_ts and self.completed_timestamp:
        return str(b32encode('%d+%d+%d'.encode() % (self.number, abs((self.completed_timestamp - self.started_ts).seconds), self._ticks)), 'utf-8')
    return str(b32encode('%d+0+%d'.encode() % (self.number, self._ticks)), 'utf-8')


Flag.calculate_code = calculate_code
