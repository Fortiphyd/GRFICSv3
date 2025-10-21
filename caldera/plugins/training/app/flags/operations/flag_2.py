from plugins.training.app.c_flag import Flag


class OperationsFlag2(Flag):
    name = 'Manual operation'

    challenge = (
        'Run and finish an operation using any adversary profile except Check. Run the operation requiring manual '
        'approval. Approve and discard links as desired.'
    )

    extra_info = (
        'During an adversary emulation exercise, operators may want to approve every command before it is tasked to an '
        'agent and executed. Operations requiring manual approval ensures that that no commands are run that the '
        'operator does not want run.'
    )

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations'):
            if op.finish and op.adversary.adversary_id != '01d77744-2515-401a-a497-d9f7241aac3c' and not op.autonomous:
                return True
        return False
