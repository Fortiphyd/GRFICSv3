import os
import random
import pyautogui
from lorem.text import TextLorem
from time import sleep
from ..utility.base_workflow import BaseWorkflow


WORKFLOW_NAME = 'OpenOfficeCalc'
WORKFLOW_DESCRIPTION = 'Create spreadsheets with Apache OpenOffice Calc (Windows)'
DEFAULT_WAIT_TIME = 2
OPEN_OFFICE_PATH = "C:\Program Files (x86)\OpenOffice 4\program\soffice"

def load():
    return OpenOfficeCalc()

class OpenOfficeCalc(BaseWorkflow):

    def __init__(self, default_wait_time=DEFAULT_WAIT_TIME, open_office_path=OPEN_OFFICE_PATH):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)
        self.default_wait_time = default_wait_time
        self.open_office_path = open_office_path

    def action(self, extra=None):
        self._create_spreadsheet()

    def _create_spreadsheet(self):
        self._new_spreadsheet()
        self._move_to_cell([random.choice('abcde'),random.randrange(6)]) # move to random cell, given column & row parameters
        sleep(1)
        self._insert_table()
        sleep(1)
        self._move_to_cell([random.choice('abcdefghijkl'),random.randrange(15)]) # move to random cell, given column & row parameters
        self._insert_comment()
        sleep(3)
        self._save_quit()

    def _insert_comment(self):
        pyautogui.hotkey('ctrl', 'alt', 'c') # insert comment
        pyautogui.typewrite(TextLorem().sentence()) # type random sentence
        pyautogui.press('esc') # finish commenting
        sleep(self.default_wait_time)

    def _new_spreadsheet(self):
        os.startfile(self.open_office_path) # start OpenOffice
        sleep(self.default_wait_time)
        pyautogui.press('s') # choose new spreadsheet
        sleep(self.default_wait_time)

    def _save_quit(self):
        pyautogui.hotkey('ctrl', 's') # save
        sleep(self.default_wait_time)
        pyautogui.typewrite(TextLorem(wsep='-', srange=(1,3)).sentence()[:-1]) # type random file name
        sleep(self.default_wait_time)
        pyautogui.press('enter')
        pyautogui.hotkey('alt','y') # choose "yes" if a popup asks if you'd like to overwrite another file
        sleep(self.default_wait_time)
        pyautogui.hotkey('ctrl','q') # quit OpenOffice

    def _move_to_cell(self, cell_coordinate):
        pyautogui.press('f5') # open navigator
        pyautogui.hotkey('ctrl','a') # select column value
        pyautogui.write(str(cell_coordinate[0])) # enter new column value
        pyautogui.press('tab') # select row value
        pyautogui.write(str(cell_coordinate[1])) # enter new row value
        pyautogui.press('enter')
        pyautogui.press('f5') # close navigator

    def _insert_table(self):
        row_length = random.randint(3,10)
        for i in range(0, row_length): # create header row for a table
            pyautogui.write(TextLorem()._word()) # type a random word
            pyautogui.press('tab')
        for j in range(0, random.randint(3,10)):
            pyautogui.press('enter')
            for k in range(0, row_length):
                pyautogui.write(str(random.randint(0,10000))) # type a random number
                pyautogui.press('tab')