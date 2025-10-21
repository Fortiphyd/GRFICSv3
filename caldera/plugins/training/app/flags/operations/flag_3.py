from plugins.training.app.c_flag import Flag


class OperationsFlag3(Flag):
    name = 'Empty operation'

    challenge = (
        'Run and finish an operation without selecting any agent groups or adversary profiles. Add at least 5 manual '
        'or potential links to the operation before finishing the operation.'
    )

    extra_info = (
       'During an autonomous adversary emulation exercise, the operation will only run tasks in the adversary profile. '
       'Manual and potential links allow an operator to "toss in" additional TTPs into a live, autonomous operation.'
    )

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations'):
            if op.finish and op.adversary.adversary_id == 'ad-hoc' and len(op.chain) >= 5 and not op.group:
                return True
        return False
