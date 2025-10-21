from plugins.training.app.c_flag import Flag


class OperationsFlag0(Flag):
    name = 'Basic operation'
    challenge = 'Run and finish an operation. Use the Check adversary profile provided in the Stockpile plugin.'
    extra_info = (
        'An autonomous operation uses an adversary profile to pre-configures the attack. Agents and C2 run '
        'without operator interference. This allows operators to run repeatable adversary emulation '
        'exercises, ensuring that each one is identical to the last.'
    )

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations'):
            if op.finish and op.adversary.adversary_id == '01d77744-2515-401a-a497-d9f7241aac3c':
                return True
        return False
