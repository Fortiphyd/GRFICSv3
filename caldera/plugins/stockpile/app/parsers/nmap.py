from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        for match in self.line(blob):
            port = self._locate_port(match)
            if port:
                for mp in self.mappers:
                    source = self.set_value(mp.source, port, self.used_facts)
                    target = self.set_value(mp.target, port, self.used_facts)
                    relationships.append(
                        Relationship(source=Fact(mp.source, source),
                                     edge=mp.edge,
                                     target=Fact(mp.target, target))
                    )
        return relationships

    @staticmethod
    def _locate_port(line):
        try:
            if 'open' in line:
                port = line.split()[0].split('/')[0]
                return int(port)
        except Exception:
            pass
        return None
