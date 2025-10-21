from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    ANTIVIRUS = ['symantec', 'norton']

    def parse(self, blob):
        relationships = []
        for match in self.line(blob.lower()):
            for uniform_match in [av for av in self.ANTIVIRUS if av in match]:
                for mp in self.mappers:
                    source = self.set_value(mp.source, uniform_match, self.used_facts)
                    target = self.set_value(mp.target, uniform_match, self.used_facts)
                    relationships.append(
                        Relationship(source=Fact(mp.source, source),
                                     edge=mp.edge,
                                     target=Fact(mp.target, target))
                    )
        return relationships
