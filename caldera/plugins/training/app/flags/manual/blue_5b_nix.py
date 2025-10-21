from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue5bNix(Flag):
    name = 'Acquire Bash Profile Hashes'
    challenge = 'Run the appropriate setup ability in the \'Blue Manual\' operation to hash all the Bash Profiles on ' \
                'the *nix machine.'
    extra_info = """"""

    async def verify(self, services):
        def bash_profiles_hashed(operation):
            return operation.ran_ability_id('df9d2b83-b40f-4167-af75-31ddde59af7e')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if bash_profiles_hashed(op):
                return True
        return False
