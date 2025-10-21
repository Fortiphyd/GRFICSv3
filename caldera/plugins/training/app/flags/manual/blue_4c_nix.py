from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue4cNix(Flag):
    name = 'Delete New Cron Job'
    challenge = 'Run the appropriate response ability in the \'Blue Manual\' operation to delete the previously ' \
                'found cron job.'
    extra_info = """"""

    async def verify(self, services):
        def is_file_deleted(operation):
            return operation.ran_ability_id('32e563bb-ba06-4bcc-b817-fc2c434c0b66')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if is_file_deleted(op):
                return True
        return False
