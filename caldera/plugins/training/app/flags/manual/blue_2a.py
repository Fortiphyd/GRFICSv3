from plugins.training.app.base_flag import BaseFlag
from plugins.training.app.c_flag import Flag
from app.utility.base_world import BaseWorld


class ManualBlue2a(Flag):
    name = 'Detect malicious file on system'
    challenge = 'Within a minute of this flag activating, a pretend malicious file will have been written on the ' \
                'Windows machine. The hash of this file will also have been written into ' \
                'C:\\Users\\Public\\malicious_files.txt. Run the appropriate detection ability in the \'Blue Manual\' ' \
                'operation to detect this file hash.'
    extra_info = """"""
    additional_fields = dict(operation_name='training_manual_2',
                             adversary_id='890508db-9646-4a2d-8d1a-4ea25b3ce02a',
                             agent_group='cert-win')

    async def verify(self, services):
        async def is_flag_satisfied():
            for op in await services.get('data_svc').locate('operations', match=dict(access=BaseWorld.Access.BLUE,
                                                                                     name='Blue Manual')):
                if await is_file_detected(op):
                    return True
            return False

        async def is_file_detected(op):
            return op.ran_ability_id('77272c88-ccf5-4225-a3d9-f9e171d1ca5b') and \
                   'file.malicious.hash' in [f.trait for f in await op.all_facts()]

        return await BaseFlag.standard_verify_with_operation(services, self.additional_fields['operation_name'],
                                                             self.additional_fields['adversary_id'],
                                                             self.additional_fields['agent_group'],
                                                             is_flag_satisfied)
