import re

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def __init__(self, parser_info):
        super().__init__(parser_info)
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']

    def nslookup_parser(self, blob):
        if blob and len(blob) > 0 and 'Non-existent domain' not in blob:
            value = re.search(r'Name:\s*(.*)\nAddress:\s*(.*)', blob)
            if value:
                return value.group(1).rstrip(), value.group(2).rstrip()

    def parse(self, blob):
        relationships = []
        fqdn, ip = self.nslookup_parser(blob)
        for mp in self.mappers:
            source = self.set_value(mp.source, fqdn, self.used_facts)
            target = self.set_value(mp.target, ip, self.used_facts)
            relationships.append(
                Relationship(source=Fact(mp.source, source),
                             edge=mp.edge,
                             target=Fact(mp.target, target)
                             )
            )
        return relationships
