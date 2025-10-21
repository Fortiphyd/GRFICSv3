from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag
from app.utility.base_world import BaseWorld


class ManualBlue3a(Flag):
    name = 'Find suspicious URL in mail'
    challenge = 'Within a minute of this flag activating, a pretend phishing email with a malicious URL will have been ' \
                'sent on the *nix machine. Run the appropriate detection ability in the \'Blue Manual\' operation to ' \
                'find this URL.'
    extra_info = """"""
    additional_fields = dict(operation_name='training_manual_3',
                             adversary_id='2c99958e-36e0-4fab-bcdf-977926a58cd6',
                             agent_group='cert-nix')

    async def verify(self, services):
        async def is_flag_satisfied():
            for op in await services.get('data_svc').locate('operations', match=dict(access=BaseWorld.Access.BLUE,
                                                                                     name='Blue Manual')):
                if await is_url_found(op):
                    return True
            return False

        async def is_url_found(op):
            return op.ran_ability_id('1226f8ec-e2e5-4311-88e7-378c0e5cc7ce') and \
                   'remote.suspicious.url' in set([f.trait for f in await op.all_facts()])

        return await BaseFlag.standard_verify_with_operation(services, self.additional_fields['operation_name'],
                                                             self.additional_fields['adversary_id'],
                                                             self.additional_fields['agent_group'],
                                                             is_flag_satisfied)
