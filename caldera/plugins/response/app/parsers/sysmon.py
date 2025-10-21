import re

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        events = [event for event in blob.split('\r\n\r\n') if event != '']
        for event in events:
            for mp in self.mappers:
                match = self.parse_options[mp.target.split('.').pop()](event)
                if match:
                    guid = [f.value for f in self.used_facts if f.trait == mp.source].pop()
                    relationships.append(Relationship(source=Fact(mp.source, guid),
                                                      edge=mp.edge,
                                                      target=Fact(mp.target, match.group(1))))
        return relationships

    @property
    def parse_options(self):
        return dict(
            eventid=self.parse_eventid,
            recordid=self.parse_recordid,
            user=self.parse_user
        )

    @staticmethod
    def parse_eventid(event):
        return re.search(r'\bId\s*: (.*)', event, re.IGNORECASE)

    @staticmethod
    def parse_recordid(event):
        return re.search(r'RecordId\s*: (.*)', event, re.IGNORECASE)

    @staticmethod
    def parse_user(event):
        return re.search(r'User: (.*)', event, re.IGNORECASE)
