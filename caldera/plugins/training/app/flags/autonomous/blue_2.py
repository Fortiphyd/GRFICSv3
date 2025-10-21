from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class AutonomousBlue2(Flag):
    name = 'Malicious file on system'
    challenge = 'Write a file on the Windows machine under the C:\\Users\\Public directory. Get the SHA256 hash of ' \
                'this file, and write it to C:\\Users\\Public\\malicious_files.txt. The autonomous defender should ' \
                'automatically find and delete the file.'
    extra_info = """"""

    async def verify(self, services):
        def is_file_deleted(operation):
            return operation.ran_ability_id('5ec7ae3b-c909-41bb-9b6b-dadec409cd40')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE,
                                                                   name='Blue Autonomous')):
            if await self._is_file_found(op) and is_file_deleted(op):
                return True
        return False
