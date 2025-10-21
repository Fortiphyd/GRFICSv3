from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):

    def parse(self, blob):
        relationships = []
        json_output = self.load_json(blob)
        if json_output:
            for mp in self.mappers:
                for child, block in json_output['roots']['bookmark_bar'].items():
                    if child == 'children':
                        self._recurse(block, relationships, mp)
        return relationships

    def _recurse(self, block, relationships, mapper, score=1):
        for child in block:
            if child.get('children'):
                self._recurse(child.get('children'), relationships, mapper, score)
            elif child.get('url'):
                source = self.set_value(mapper.source, child.get('name'), self.used_facts)
                target = self.set_value(mapper.target, child.get('url'), self.used_facts)
                if child.get('meta_info', dict()).get('last_visited_desktop'):
                    if int(child['meta_info']['last_visited_desktop']) > score:
                        score += 1
                relationships.append(Relationship(source=Fact(mapper.source, source),
                                                  edge=mapper.edge,
                                                  target=Fact(mapper.target, target),
                                                  score=score))
