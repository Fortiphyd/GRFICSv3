import json

from plugins.training.app.c_flag import Flag
from app.utility.base_object import BaseObject


class Navigator(Flag, BaseObject):
    """
    Type of flag that checks if a provided ATT&CK Navigator layer file contains the required (Tactic, Technique)
    mappings
    """
    answer = None

    def __init__(self, number):
        super().__init__(number)
        self.flag_type = 'navigator'

    @property
    def display(self):
        return dict(number=self.number, name=self.name, challenge=self.challenge, flag_type=self.flag_type,
                    completed=self.completed, extra_info=self.extra_info, code=self.calculate_code(),
                    completed_timestamp=self._convert_timestamp())

    def verify(self, blob):
        layer = json.loads(blob)
        tact_tech_list = [(technique['tactic'], technique['techniqueID']) for technique in layer['techniques']]
        guess = self._sort_tactic_technique(tact_tech_list)
        answer = self._sort_tactic_technique(self.answer)
        return guess == answer

    @staticmethod
    def _sort_tactic_technique(tact_tech_list):
        tactics = {}
        for tactic, t_id in tact_tech_list:
            if tactic in tactics.keys():
                tactics[tactic].append(t_id)
            else:
                tactics[tactic] = [t_id]
        for t in tactics:
            tactics[t] = sorted(tactics[t])
        return tactics
