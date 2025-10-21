from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class ManualBlue4aNix(Flag):
    name = 'Acquire Cron Jobs Baseline'
    challenge = 'Run the appropriate setup ability in the \'Blue Manual\' operation to acquire a list of currently ' \
                'existing cron jobs on the *nix machine.'
    extra_info = """"""

    async def verify(self, services):
        def cron_jobs_baseline_found(operation):
            return operation.ran_ability_id('ba907d7a-b334-47e7-b652-4e481b5aa534')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Manual')):
            if cron_jobs_baseline_found(op):
                return True
        return False
