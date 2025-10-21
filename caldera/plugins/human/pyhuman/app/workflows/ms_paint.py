import os
from importlib import import_module
from time import sleep, time

from ..utility.base_workflow import BaseWorkflow


WORKFLOW_NAME = 'MicrosoftPaint'
WORKFLOW_DESCRIPTION = 'Create a blank MS Paint file (Windows)'

DEFAULT_INPUT_WAIT_TIME = 2
DEFAULT_PAINT_PATH = paint_path = 'C:\Windows\System32\mspaint.exe'


def load():
    pyautogui = import_module('pyautogui')
    return msPaint(pyautogui=pyautogui)


class msPaint(BaseWorkflow):

    def __init__(self, pyautogui, input_wait_time=DEFAULT_INPUT_WAIT_TIME, paint_path=DEFAULT_PAINT_PATH):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)

        self.pyautogui = pyautogui
        self.input_wait_time = input_wait_time
        self.paint_path = paint_path

    def action(self, extra=None):
        self._ms_paint()

    """ PRIVATE """

    def _ms_paint(self):
        os.startfile(self.paint_path)
        self.pyautogui.getWindowsWithTitle('Paint')
        sleep(self.input_wait_time)
        self.pyautogui.hotkey('ctrl', 's')
        file_name = int(time())
        sleep(self.input_wait_time)
        self.pyautogui.typewrite(str(file_name))
        sleep(self.input_wait_time)
        self.pyautogui.press('enter')
        sleep(self.input_wait_time)
        self.pyautogui.getWindowsWithTitle('Paint')
        self.pyautogui.hotkey('alt', 'f4')
