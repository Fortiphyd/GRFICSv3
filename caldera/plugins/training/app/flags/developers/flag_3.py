import socket
from plugins.training.app.c_flag import Flag


class DevelopersFlag3(Flag):
    name = 'Write new parser'
    challenge = 'Add a new parser which parses IPV6 addresses with the trait, "host.ip.ipv6". ' \
                'Then run an adversary which correctly parses out matching facts. Hint: use the ability you created ' \
                'in an earlier flag.'
    extra_info = ''

    async def verify(self, services):
        def _valid_ipv6(n):
            try:
                socket.inet_pton(socket.AF_INET6, n)
                return True
            except socket.error:
                return False

        for op in await services.get('data_svc').locate('operations'):
            if op.finish:
                found_fact = [fact for fact in await op.all_facts() if fact.trait == 'host.ip.ipv6'
                              and len(fact.value.split(':')) == 8 and _valid_ipv6(fact.value.split(':'))]
                if len(found_fact) > 0:
                    return True
        return False
