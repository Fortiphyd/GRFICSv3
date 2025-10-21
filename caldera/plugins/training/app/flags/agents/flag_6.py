from plugins.training.app.c_flag import Flag


class AgentsFlag6(Flag):
    name = 'Contact points'
    challenge = 'Deploy a new agent, using a different contact point then your first agent'
    extra_info = (
        'If an adversary deploys all of their agents on a host using the same protocol, say HTTP, then when '
        'their agent is detected and shut down, the defenders will likely close access to the C2 over that protocol. '
        'Therefore, an adversary will want multiple agents on a host, each using a different protocol to talk to '
        'the C2.'
    )

    async def verify(self, services):
        contacts = set([agent.contact for agent in await services.get('data_svc').locate('agents')])
        if len(contacts) > 1:
            return True
        return False
