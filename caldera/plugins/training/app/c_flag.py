import abc
import os
from datetime import datetime

import markdown

from app.utility.base_object import BaseObject


class Flag(BaseObject):
    name = None
    challenge = None
    extra_info = None
    additional_fields = None

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, v):
        self._completed = v
        self._completed_timestamp = datetime.now()

    @property
    def completed_timestamp(self):
        return self._completed_timestamp

    @property
    def started_ts(self):
        return self._started_ts

    @property
    def display(self):
        return dict(number=self.number, name=self.name, challenge=self.challenge, completed=self.completed,
                    extra_info=self.extra_info, code=self.calculate_code(),
                    completed_timestamp=self._convert_timestamp(),
                    resettable=self._is_resettable(),
                    has_solution_guide = self.has_solution_guide)

    @property
    def solution_guide_filename(self):
        return f'{self.__class__.__name__}.md'

    @property
    def solution_guide_path(self):
        import plugins.training  # avoiding an import cycle

        return os.path.join(
            plugins.training.PLUGIN_DIR,
            'solution_guides',
            self.solution_guide_filename
        )

    @property
    def has_solution_guide(self):
        return os.path.exists(self.solution_guide_path)

    def __init__(self, number):
        super().__init__()
        self.number = number
        self._completed = False
        self._completed_timestamp = None
        self._started_ts = None
        self._ticks = 0

    @abc.abstractmethod
    def verify(self, services):
        """
        Determines whether a flag's challenge has been met or not
        :param services:
        :return: boolean True if flag challenge is met, False otherwise
        """
        pass

    def store(self, ram):
        existing = self.retrieve(ram['flags'], self.unique)
        if not existing:
            ram['flags'].append(self)
            return self.retrieve(ram['flags'], self.unique)
        return existing

    def activate(self):
        if not self._started_ts:
            self._started_ts = datetime.now()
        if not self._completed_timestamp:
            self._ticks += 1

    def calculate_code(self):
        return self.unique

    def solution_guide_as_html(self):
        with open(self.solution_guide_path, encoding='utf-8') as f:
            return markdown.markdown(f.read())

    def _convert_timestamp(self):
        return self.completed_timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.completed_timestamp else ''

    def _is_resettable(self):
        return 'True' if self.additional_fields and 'adversary_id' in self.additional_fields else 'False'

    @staticmethod
    def _is_unauth_process_killed(op):
        return op.ran_ability_id('02fb7fa9-8886-4330-9e65-fa7bb1bc5271')

    @staticmethod
    async def _is_unauth_process_detected(op):
        operation_traits = set(f.trait for f in await op.all_facts())
        return op.ran_ability_id('3b4640bc-eacb-407a-a997-105e39788781') and \
            'remote.port.unauthorized' in operation_traits and \
            'host.pid.unauthorized' in operation_traits

    @staticmethod
    async def _is_file_found(op):
        operation_traits = set(f.trait for f in await op.all_facts())
        return op.ran_ability_id('f9b3eff0-e11c-48de-9338-1578b351b14b') and \
            'file.malicious.hash' in operation_traits and \
            'host.malicious.file' in operation_traits
