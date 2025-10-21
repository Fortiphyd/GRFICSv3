from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag
from app.utility.base_world import BaseWorld


class ManualBlue1a(Flag):
    name = 'Detect process on Unauthorized Port'
    challenge = 'Within a minute of this flag activating, a listening process will have been started on port 7011 on ' \
                'the *nix machine. Run the appropriate detection ability in the \'Blue Manual\' operation to detect ' \
                'this process.'
    extra_info = """"""
    additional_fields = dict(operation_name='training_manual_1',
                             adversary_id='72c0b333-f6fe-4fa0-a342-4215e8de3947',
                             agent_group='cert-nix')

    async def verify(self, services):
        async def is_flag_satisfied():
            for op in await services.get('data_svc').locate('operations',
                                                            match=dict(access=BaseWorld.Access.BLUE,
                                                                       name='Blue Manual')):
                if await self._is_unauth_process_detected(op):
                    return True
            return False

        return await BaseFlag.standard_verify_with_operation(services, self.additional_fields['operation_name'],
                                                             self.additional_fields['adversary_id'],
                                                             self.additional_fields['agent_group'],
                                                             is_flag_satisfied)
