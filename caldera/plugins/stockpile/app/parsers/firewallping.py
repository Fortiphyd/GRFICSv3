from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for match in self.line(blob):
            if match.startswith('    Packets'):
                if '(0%' in match:
                    for mp in self.mappers:
                        source = self.set_value(mp.source, match, self.used_facts)
                        relationships.append(
                            Relationship(source=Fact(mp.source, source),
                                         edge=mp.edge,
                                         target=Fact(mp.target, None))
                        )
        return relationships
