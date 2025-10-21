from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class AgentsFlag2(Flag):
    name = 'Understanding trust'
    challenge = 'Change the untrusted agent timer to 60 seconds.'
    extra_info = (
        'Agents beacon into the C2 on a regular basis, asking the adversary if there are new instructions. '
        'If a beacon misses a regularly scheduled interval, there is a chance the agent itself has been discovered and '
        'compromised. Defenders may attempt to reverse-engineer the agent and restart it with the intent of '
        'learning how it works.'
    )

    async def verify(self, services):
        if BaseWorld.get_config(name='agents', prop='untrusted_timer') == 60:
            return True
        return False
