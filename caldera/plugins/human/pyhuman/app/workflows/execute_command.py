import subprocess

from ..utility.base_workflow import BaseWorkflow


WORKFLOW_NAME = 'ExecuteCommand'
WORKFLOW_DESCRIPTION = 'Execute custom commands'


def load():
    return ExecuteCommand()


class ExecuteCommand(BaseWorkflow):

    def __init__(self):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)

    @staticmethod
    def action(extra=None):
        for c in extra:
            subprocess.Popen(c, shell=True)
