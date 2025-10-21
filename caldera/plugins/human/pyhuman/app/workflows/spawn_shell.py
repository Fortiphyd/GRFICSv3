import subprocess
import sys
from time import sleep

from ..utility.base_workflow import BaseWorkflow


WORKFLOW_NAME = 'ListFiles'
WORKFLOW_DESCRIPTION = 'List files in the current directory'


def load():
    return ListFiles()


class ListFiles(BaseWorkflow):

    def __init__(self):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)

    def action(self, extra=None):
        self._spawn_shell_and_quit()

    """ PRIVATE """

    def _spawn_shell_and_quit(self):
        p = subprocess.Popen(self._determine_os_shell_command(), shell=True)
        sleep(5)
        p.kill()

    @staticmethod
    def _determine_os_shell_command():
        if sys.platform.startswith('win32') or sys.platform.startswith('cygwin'):
            return 'dir'
        return 'ls -la'
