import os

from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class DevelopersFlag4(Flag):
    name = 'Add new blue ability'
    challenge = 'Add a new detection ability - manually - to the Response plugin which displays all user names on a ' \
                'host. Ensure this ability will run more than once if used in an operation, then ensure it is ' \
                'loaded into the database. The ability ID should be abc123.'
    extra_info = ''

    async def verify(self, services):
        check1, check2 = False, False
        if os.path.isfile('plugins/response/data/abilities/detection/abc123.yml'):
            check1 = True
            for a in await services.get('data_svc').locate('abilities', dict(ability_id='abc123')):
                if a.access == BaseWorld.Access.BLUE and a.repeatable:
                    check2 = True
            return all([check1, check2])
