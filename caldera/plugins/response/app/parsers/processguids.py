import re

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        all_facts = self.used_facts
        for mp in self.mappers:
            matches = self.parse_options[mp.target.split('.').pop()](blob)
            for match in matches:
                src_fact_value = [f.value for f in all_facts if f.trait == mp.source].pop()
                r = Relationship(source=Fact(mp.source, src_fact_value),
                                 edge=mp.edge,
                                 target=Fact(mp.target, match))
                relationships.append(r)
                all_facts.append(r.target)
        return relationships

    @property
    def parse_options(self):
        return dict(
            id=self.parse_id,
            guid=self.parse_guid,
            parentid=self.parse_parentid,
            parentguid=self.parse_parentguid
        )

    @staticmethod
    def parse_id(blob):
        return re.findall(r'\bProcessId: (.*)', blob, re.IGNORECASE)

    @staticmethod
    def parse_guid(blob):
        return re.findall(r'\bProcessGuid:\W+{(.*)}', blob, re.IGNORECASE)

    @staticmethod
    def parse_parentid(blob):
        return re.findall(r'\bParentProcessId: (.*)', blob, re.IGNORECASE)

    @staticmethod
    def parse_parentguid(blob):
        return re.findall(r'\bParentProcessGuid:\W+{(.*)}', blob, re.IGNORECASE)
