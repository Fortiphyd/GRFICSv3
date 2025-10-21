from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag
from app.utility.base_world import BaseWorld


class ManualBlue4bNix(Flag):
    name = 'Find New Unauthorized Cron Job'
    challenge = 'Within a minute of this flag activating, a new cron job will have been installed on the *nix machine. ' \
                'Run the appropriate detection ability in the \'Blue Manual\' operation to find this cron job.'
    extra_info = """"""
    additional_fields = dict(operation_name='training_manual_4a',
                             adversary_id='9fbc7164-9175-4fc6-bb20-9669dc121df8',
                             agent_group='cert-nix')

    async def verify(self, services):
        async def is_flag_satisfied():
            for op in await services.get('data_svc').locate('operations', match=dict(access=BaseWorld.Access.BLUE,
                                                                                     name='Blue Manual')):
                if await is_cronjob_found(op):
                    return True
            return False

        async def is_cronjob_found(op):
            operation_traits = set(f.trait for f in await op.all_facts())
            return op.ran_ability_id('ee54384f-cfbc-4228-9dc1-cc5632307afb') and \
                'host.user.name' in operation_traits and \
                'host.new.cronjob' in operation_traits

        return await BaseFlag.standard_verify_with_operation(services, self.additional_fields['operation_name'],
                                                             self.additional_fields['adversary_id'],
                                                             self.additional_fields['agent_group'],
                                                             is_flag_satisfied)
