import sys

from plugins.training.app.c_flag import Flag


class AgentsFlag1(Flag):
    name = 'Remote agent'

    challenge = (
        'Demonstrate your ability to deploy an agent on a remote host. The agent should successfully '
        'beacon back to this server instance. This agent should be run on an operating system that is NOT '
        'the same as what is hosting the server (Hint: If running caldera on any flavor of Linux, use a '
        'Windows or Mac for remote host). It is OK to use a virtual box to complete this challenge.'
    )

    extra_info = (
        'Adversaries will most likely deploy their command-and-control (C2) server somewhere Internet '
        'accessible. This means their agents will need to have access to the C2 IP address. Computers often have '
        'unrestricted outbound Internet connectivity but heavily restricted inbound connectivity, which is why '
        'it\'s usually best to have an agent connect to you, not vice-versa.'
    )

    async def verify(self, services):
        agents = await services.get('data_svc').locate('agents')
        check1 = len(agents) > 1
        check2, check3 = False, False
        for a in agents:
            if a.platform != sys.platform:
                check2 = True
            if a.server not in ['127.0.0.1', 'localhost', '0.0.0.0']:
                check3 = True
        return all([check1, check2, check3])
