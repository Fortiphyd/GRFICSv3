from plugins.training.app.c_flag import Flag


class AdvancedFlag1(Flag):
    name = 'Adjust sources'
    challenge = 'Create a new fact source called "better basic" with at least 1 fact and 1 rule'
    extra_info = (
        'Fact sources are used to seed an operation with facts and put rules in place to determine which facts will be '
        'saved during the operation.'
    )

    async def verify(self, services):
        for source in await services.get('data_svc').locate('sources', dict(name='better basic')):
            if source.facts and source.rules:
                return True
        return False
