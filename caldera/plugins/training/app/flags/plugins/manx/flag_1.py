from plugins.training.app.c_flag import Flag


class PluginsManxFlag1(Flag):
    name = 'Manx UDP'
    challenge = 'Start a new Manx agent in UDP mode'
    extra_info = (
        'If an adversary is having trouble getting an agent to connect outbound over popular protocols, like '
        'HTTP or TCP, they will often fallback to UDP. Because DNS goes over UDP, this protocol is usually more '
        'accessible than others. In addition, lazy system administrators may forget to add firewall rules on UDP '
        'ports whereas TCP is the default in most firewall tools.'
    )

    async def verify(self, services):
        for _ in await services.get('data_svc').locate('agents', dict(contact='udp')):
            return True
        return False
