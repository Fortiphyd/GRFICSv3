import re

from ipaddress import ip_address

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):
    exclude = ['0.0.0.0', '127.0.0.1']
    subnet_exclude = ['.255', '.0', '.1']

    def parse(self, blob):
        IPs = []
        for ip in re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', blob):
            if self._is_valid_ip(ip):
                for mp in self.mappers:
                    IPs.append(Relationship(source=Fact(trait=mp.source, value=ip),
                                            edge=mp.edge,
                                            target=Fact(mp.target, '')))
        return IPs

    def _is_valid_ip(self, raw_ip):
        try:
            # The following hardcoded addresses are not used to bind to an interface.
            if raw_ip in self.exclude:
                return False
            if any([True if raw_ip.endswith(x) else None for x in self.subnet_exclude]):
                return False
            ip_address(raw_ip)
        except Exception:
            return False
        return True
