import json
import logging

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def __init__(self, parser_info):
        super().__init__(parser_info)
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.log = logging.getLogger('parsing_svc')

    def parse(self, blob):
        relationships = []
        json_output = self.load_json(blob)
        if json_output is not None:
            for mp in self.mappers:
                if 'json_key' not in mp.custom_parser_vals.keys():
                    self.log.warning('JSON Parser not given a json_key, not parsing')
                    continue
                json_type = mp.custom_parser_vals['json_type'] if 'json_type' in mp.custom_parser_vals.keys() else None
                for match in self._get_vals_from_json(json_output, mp.custom_parser_vals['json_key'], json_type):
                    source = self.set_value(mp.source, match, self.used_facts)
                    target = self.set_value(mp.target, match, self.used_facts)
                    relationships.append(
                        Relationship(source=Fact(mp.source, source),
                                     edge=mp.edge,
                                     target=Fact(mp.target, target))
                    )
        return relationships

    def _get_vals_from_json(self, json_output, key, json_type):
        """
        Get all values for a specified key recursively from JSON output.
        :param json_output:
        :param key:
        :param json_type: a type to filter matches by. Example options are - 'str', 'int', 'list', 'dict'
        :return: generator that yields matched values
        """
        if isinstance(json_output, list):
            for item in json_output:
                for res in self._get_vals_from_json(item, key, json_type):
                    yield res
        elif isinstance(json_output, dict):
            for k, v in json_output.items():
                if k == key and (json_type is None or v.__class__.__name__ == json_type):
                    yield json.dumps(v) if v.__class__.__name__ in ['list', 'dict'] else v
                if isinstance(v, list) or isinstance(v, dict):
                    for res in self._get_vals_from_json(v, key, json_type):
                        yield res
