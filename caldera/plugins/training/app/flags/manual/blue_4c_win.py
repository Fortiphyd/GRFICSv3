from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue4cWin(Flag):
    name = 'Delete New Scheduled Task'
    challenge = 'Run the appropriate response ability in the \'Blue Manual\' operation to delete the previously ' \
                'found scheduled task.'
    extra_info = """"""

    async def verify(self, services):
        def is_file_deleted(operation):
            return operation.ran_ability_id('4744d99f-5fea-42a8-8ec4-c228db57caea')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if is_file_deleted(op):
                return True
        return False
