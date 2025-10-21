from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue5dNix(Flag):
    name = 'Restore Modified Bash Profile'
    challenge = 'Run the appropriate response ability in the \'Blue Manual\' operation to restore the previously ' \
                'found modified Bash Profile with its backup.'
    extra_info = """"""

    async def verify(self, services):
        def is_modified_profile_restored(operation):
            return operation.ran_ability_id('e846973a-767b-4f9c-8b9e-5249cfcd7b97')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if is_modified_profile_restored(op):
                return True
        return False
