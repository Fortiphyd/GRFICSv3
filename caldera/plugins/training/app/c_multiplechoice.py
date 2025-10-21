from plugins.training.app.c_flag import Flag
from app.utility.base_object import BaseObject


class MultipleChoice(Flag, BaseObject):
    answer = None
    options = None
    multi_select = False

    def __init__(self, number):
        super().__init__(number)
        self.flag_type = 'multiplechoice'

    @property
    def display(self):
        return dict(number=self.number, name=self.name, challenge=self.challenge, options=self.options,
                    multi_select=self.multi_select, flag_type=self.flag_type, completed=self.completed,
                    extra_info=self.extra_info, code=self.calculate_code(),
                    completed_timestamp=self._convert_timestamp())

    def verify(self, answer):
        return answer == self.answer
