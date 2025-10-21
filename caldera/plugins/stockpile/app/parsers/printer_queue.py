from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser
import re


class Parser(BaseParser):
    def parse(self, blob):
        relationships = []
        for match in self.line(blob):
            # Ignore this row if it's a heading or doesn't contain queued document info
            first_char = match[0]
            if not first_char.isnumeric():
                continue

            split_match = re.split(" +", match)
            file_name = " ".join(split_match[3:-2])
            file_size = " ".join(split_match[-2:])

            for mp in self.mappers:
                source = self.set_value(mp.source, file_name, self.used_facts)
                target = self.set_value(mp.target, file_size, self.used_facts)
                relationships.append(
                    Relationship(source=Fact(mp.source, source),
                                 edge=mp.edge,
                                 target=Fact(mp.target, target))
                )

        return relationships
