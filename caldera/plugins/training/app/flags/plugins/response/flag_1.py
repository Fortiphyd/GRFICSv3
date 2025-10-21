from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class PluginsResponseFlag1(Flag):
    name = 'Blue operation'

    challenge = (
        'Using the machine with the blue agent, connect to a listener on another machine listening on TCP '
        'port 7011. This can be done using Netcat on *nix machines, or TcpClient on Windows machines.'
        'Then, run a blue operation using the blue agent group, the \'Incident responder\' defender, the '
        'batch planner and the response fact source.'
    )

    extra_info = (
        'EDR agents are intended to run at all times while the endpoint is running. To simulate this, '
        'agents can be registered on endpoints to automatically run when the endpoint is booted. Defenders '
        'can also be instructed to run continuously through the use of Repeatable abilities.'
    )

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations', dict(access=BaseWorld.Access.BLUE)):
            if len(op.agents) and op.group == 'blue' and \
                    op.adversary.adversary_id == '7e422753-ad7a-4401-bc8b-b12a28e69c25':
                if self._is_unauth_process_killed(op):
                    return True
        return False
