from plugins.training.app.c_flag import Flag


class AgentsFlag0(Flag):
    name = 'Local agent'

    challenge = (
        'Demonstrate your ability to deploy an agent on local host. The agent should successfully '
        'beacon back to this server instance.'
    )

    extra_info = (
        'An agent is another name for Remote Access Trojan (RAT). These programs, written in any language, '
        'execute an adversary\'s instructions on compromised computers. Often, an agent will communicate back to the '
        'adversary through an internet protocol, such as HTTP, UDP or DNS. Agents give adversaries remote-control '
        'access of the computer running it.'
    )

    async def verify(self, services):
        return len(await services.get('data_svc').locate('agents')) > 0
