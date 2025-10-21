from plugins.training.app.c_flag import Flag
from app.utility.base_object import BaseObject


class FillInBlank(Flag, BaseObject):
    answer = None

    def __init__(self, number):
        super().__init__(number)
        self.flag_type = 'fillinblank'

    @property
    def display(self):
        return dict(number=self.number, name=self.name, challenge=self.challenge, flag_type=self.flag_type,
                    completed=self.completed, extra_info=self.extra_info, code=self.calculate_code(),
                    completed_timestamp=self._convert_timestamp())

    def verify(self, answer):
        return answer.lower() == self.answer
