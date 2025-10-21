from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag
from app.utility.base_world import BaseWorld


class ManualBlue4bWin(Flag):
    name = 'Find New Unauthorized Scheduled Task'
    challenge = 'Within a minute of this flag activating, a new scheduled task will have been registered on the ' \
                'windows machine. Run the appropriate detection ability in the \'Blue Manual\' operation to find ' \
                'this cron job.'
    extra_info = """"""
    additional_fields = dict(operation_name='training_manual_4b',
                             adversary_id='9fbc7164-9175-4fc6-bb20-9669dc121df8',
                             agent_group='cert-win')

    async def verify(self, services):
        async def is_flag_satisfied():
            for op in await services.get('data_svc').locate('operations', match=dict(access=BaseWorld.Access.BLUE,
                                                                                     name='Blue Manual')):
                if await is_cronjob_found(op):
                    return True
            return False

        async def is_cronjob_found(op):
            return op.ran_ability_id('8bc73098-54d1-4f69-abd5-271e3e2da5df') and \
                   'host.new.schtask' in set(f.trait for f in await op.all_facts())

        return await BaseFlag.standard_verify_with_operation(services, self.additional_fields['operation_name'],
                                                             self.additional_fields['adversary_id'],
                                                             self.additional_fields['agent_group'],
                                                             is_flag_satisfied)
