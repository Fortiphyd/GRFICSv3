from plugins.training.app.c_flag import Flag


class OperationsFlag1(Flag):
    name = 'Stealthy operation'

    challenge = (
        'Run and finish an operation using a jitter of 10/20 and base64 obfuscation. Use the Check adversary profile '
        'provided in the Stockpile plugin again.'
    )

    extra_info = (
        'Adding a random sleep time (jitter) between each command an agent runs is equally as important for '
        'staying undetected as is using random beacon intervals.\n'
        'Another way to stay undetected is to obfuscate commands. Defenders will often write monitors to '
        'detect specific keywords used on a host. If an adversary obfuscates their commands, they can bypass '
        'this sort of detection tactic.'
    )

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations'):
            if op.finish and op.adversary.adversary_id == '01d77744-2515-401a-a497-d9f7241aac3c' \
                    and op.obfuscator == 'base64' and op.jitter == '10/20':
                return True
        return False
