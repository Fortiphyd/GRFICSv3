from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue2c(Flag):
    name = 'Delete malicious file on system'
    challenge = 'Run the appropriate response ability in the \'Blue Manual\' operation to delete the previously ' \
                'found malicious file.'
    extra_info = """"""

    async def verify(self, services):
        def is_file_deleted(operation):
            return operation.ran_ability_id('5ec7ae3b-c909-41bb-9b6b-dadec409cd40')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if is_file_deleted(op):
                return True
        return False
