from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag
from app.utility.base_world import BaseWorld


class ManualBlue3b(Flag):

    name = 'Inoculate suspicious URL'
    challenge = 'Run the appropriate response ability in the \'Blue Manual\' operation to inoculate the previously ' \
                'found URL.'
    extra_info = """"""
    additional_fields = dict(operation_name='training_manual_3_cleanup',
                             adversary_id='2885d0fe-60a7-469b-9e2e-a46b7be2b4df',
                             agent_group='cert-nix')

    async def verify(self, services):
        async def is_flag_satisfied():
            for op in await services.get('data_svc').locate('operations',
                                                            match=dict(access=BaseWorld.Access.BLUE,
                                                                       name='Blue Manual')):
                if is_url_inoculated(op):
                    return True
            return False

        def is_url_inoculated(op):
            return op.ran_ability_id('2ca64acd-dc12-4cc8-b78a-6a182508a50b')

        return await BaseFlag.standard_verify_with_operation(services, self.additional_fields['operation_name'],
                                                             self.additional_fields['adversary_id'],
                                                             self.additional_fields['agent_group'],
                                                             is_flag_satisfied)
