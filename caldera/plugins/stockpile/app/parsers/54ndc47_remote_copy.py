from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_fact import Fact
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    ABILITY_SUCCESS_FLAG = 'VERBOSE: Performing the operation "Copy'

    def parse(self, blob):
        relationships = []
        for match in self.line(blob):
            if self.ABILITY_SUCCESS_FLAG in match:
                for mp in self.mappers:
                    relationships.append(
                        Relationship(source=Fact(mp.source, self._get_remote_host(mp.source, self.used_facts)),
                                     edge=mp.edge,
                                     target=Fact(mp.target, None))
                    )
                # we can only have one resulting relationship in this parser type. return immediately
                return relationships
        return relationships

    """ PRIVATE """

    @staticmethod
    def _get_remote_host(source_trait, used_facts):
        for uf in used_facts:
            if uf.trait == source_trait:
                return uf.value
