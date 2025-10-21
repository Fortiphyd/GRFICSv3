import re

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for share in re.findall(r'^(.+?)\s+(Disk|IPC)', blob, re.MULTILINE):
            for mp in self.mappers:
                all_facts = self.used_facts.copy()
                all_facts.extend(self.source_facts)
                fqdn = [f.value for f in all_facts if f.trait == mp.source].pop()
                source = self.set_value(mp.source, fqdn, self.used_facts)
                target = self.set_value(mp.target, share[0], self.used_facts)
                relationships.append(
                    Relationship(source=Fact(mp.source, source),
                                 edge=mp.edge,
                                 target=Fact(mp.target, target))
                )
        return relationships
