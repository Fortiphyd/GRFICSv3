from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue0(Flag):
    name = 'Enable Manual Operation'
    challenge = 'Start a manual blue operation by not specifying any defender profiles. Name this operation exactly ' \
                '\'Blue Manual\'. Keep this operation open to successfully complete the flags for this badge.'
    extra_info = """"""

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if op.adversary.adversary_id == 'ad-hoc':
                return True
        return False
