from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue4aWin(Flag):
    name = 'Acquire Scheduled Tasks Baseline'
    challenge = 'Run the appropriate setup ability in the \'Blue Manual\' operation to acquire a list of currently ' \
                'existing scheduled tasks on the Windows machine.'
    extra_info = """"""

    async def verify(self, services):
        def is_baseline_acquired(operation):
            return operation.ran_ability_id('a65a62e1-b8c0-4f88-b564-166e7499d560')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if is_baseline_acquired(op):
                return True
        return False
