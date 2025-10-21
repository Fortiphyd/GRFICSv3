from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class AgentsFlag5(Flag):
    name = 'Bootstrap abilities'

    challenge = (
        'Using a Stockpile ability, ensure new agents automatically run "whoami" on their first beacon. '
        'Locate the ability that executes this command and enter the ability id as a bootstrap ability '
        '(Hint: Abilities can be found in the `plugins/stockpile/data/abilities` directory).'
    )

    extra_info = (
        'Depending on the defensive tools installed on a compromised machine, an adversary may need to '
        'execute their mission quickly before getting detected and shut down. One common tactic is to give '
        'each new agent a set of instructions to run immediately after sending the first beacon in. These '
        'instructions may determine what software is installed on the host, to gain persistence or any another tactic.'
    )

    async def verify(self, services):
        abilities = BaseWorld.get_config(name='agents', prop='bootstrap_abilities')
        return 'c0da588f-79f0-4263-8998-7496b1a40596' in abilities
