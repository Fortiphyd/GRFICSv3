from app.utility.base_parser import BaseParser
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for match in self.broadcastip(blob):
            for mp in self.mappers:
                source = self.set_value(mp.source, match, self.used_facts)
                target = self.set_value(mp.target, match, self.used_facts)
                relationships.append(
                    Relationship(source=Fact(mp.source, source),
                                 edge=mp.edge,
                                 target=Fact(mp.target, target))
                )
        return relationships
