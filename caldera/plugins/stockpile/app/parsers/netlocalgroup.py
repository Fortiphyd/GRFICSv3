import logging
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser

class Parser(BaseParser):
    def __init__(self, parser_info):
        super().__init__(parser_info)
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.log = logging.getLogger('Parser')
        
    def extract(self, text):
        try:
            users = []
            skip = text.find("ComputerName")
            skip2 = text.find("WARNING", 1)
            safe = text[skip:skip2]
            for block in safe.split("\r\n\r\n"):
                lines = block.splitlines()
                parsed_block = {}
                for line in lines:
                    if ':' in line:
                        k, v = line.split(':')
                        parsed_block[k.strip()] = v.strip().lower()
                    else:
                        continue
                # block_dict = {x.strip(): y.strip() for x, y in line.split(':') for line in lines}
                if len(parsed_block) and '\\' in parsed_block.get('MemberName'):
                    domain, user = parsed_block['MemberName'].split('\\')
                    if user != '':  # remove orphaned users
                        sid = parsed_block.get('SID')
                        is_domain = True if parsed_block.get('IsDomain') == "true" else False
                        is_group = True if parsed_block.get('IsGroup') == "true" else False
                        
                        new_user_dict = {}
                        new_user_dict['username'] = user
                        new_user_dict['is_group'] = is_group
                        new_user_dict['sid'] = sid
                        if is_domain:
                            new_user_dict['windows_domain'] = domain
                        else:
                            new_user_dict['hostname'] = domain
                        users.append(new_user_dict)
            if not users:
                self.log.warning("Net-LocalGroup Parser: Returned data contained no parseable users!")
            return users
        except Exception as e:
            self.log.warning(f"Net-LocalGroup Parser: Data format in return:{e}\n  {text}")
            
    def parse(self, blob):
        relationships = []
        data = self.extract(blob)
        check_admin = True
        for entry in data:
            if not entry['is_group'] and 'windows_domain' in entry:
                for mp in self.mappers:
                    username = entry['username']
                    if not username.startswith(entry['windows_domain']):
                        username = entry['windows_domain'] + '\\' + username
                    source = self.set_value(mp.source, self.used_facts[0].trait, self.used_facts)
                    target = self.set_value(mp.target, username, self.used_facts)
                    check_admin = False
                    relationships.append(
                        Relationship(source=Fact(mp.source, source),
                                     edge=mp.edge,
                                     target=Fact(mp.target, target))
                    )
        if check_admin:
            relationships.append(
                Relationship(source=Fact("backup.admin.ability", "get_admin"), edge="first_failed",
                             target=Fact("dummy.fact.variable", None))
            )
        return relationships
