from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue1b(Flag):
    name = 'Kill process on Unauthorized Port'
    challenge = 'Run the appropriate response ability in the \'Blue Manual\' operation to kill the previously found ' \
                'process.'
    extra_info = """"""

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if self._is_unauth_process_killed(op):
                return True
        return False
