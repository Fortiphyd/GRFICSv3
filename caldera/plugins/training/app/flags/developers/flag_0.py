import glob
from plugins.training.app.c_flag import Flag


class DevelopersFlag0(Flag):
    name = 'Create a new plugin'
    challenge = 'Build a new plugin named "abilities" where a GUI page displays all the abilities which are ' \
                'in the database.'
    extra_info = ''

    async def verify(self, services):
        check1, check2 = False, False
        for _ in await services.get('data_svc').locate('plugins', dict(enabled=True, name='abilities')):
            check1 = True
            for filename in glob.iglob('plugins/abilities/**/*.html'):
                with open(filename, 'r') as f:
                    content = f.read()
                    if 'abilities' in content and 'endfor' in content:
                        check2 = True
        return all([check1, check2])
