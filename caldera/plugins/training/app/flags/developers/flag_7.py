from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class DevelopersFlag7(Flag):
    name = 'Understanding access'
    challenge = 'Change the access of the GameBoard plugin so only blue-team users can access it'
    extra_info = """In a shared C2, you may want to restrict access to specific areas for some users."""

    async def verify(self, services):
        for plugin in await services.get('data_svc').locate('plugins', dict(name='gameboard')):
            return plugin.access == BaseWorld.Access.BLUE
        return False
