from app.utility.base_parser import BaseParser
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        vm_names = self._get_vm_names(blob)
        for name in vm_names:
            for mp in self.mappers:
                relationships.append(
                    Relationship(source=Fact(mp.source, name),
                                 edge=mp.edge,
                                 target=Fact(mp.target, None))
                )
        return relationships

    """ PRIVATE """

    @staticmethod
    def _get_vm_names(blob):
        vm_names = []
        for line in blob.split('\n'):
            line = line.split('\t\t')
            vm_names.append(line[0])
        return vm_names
