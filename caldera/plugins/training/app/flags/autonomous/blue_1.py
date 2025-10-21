from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class AutonomousBlue1(Flag):
    name = 'Process on Unauthorized Port'
    challenge = 'Start a listening process on Port 7011 on the Linux or Darwin machine (`nc -l 7011` should work). ' \
                'The autonomous defender created in the last flag (Incident Responder defender profile, batch ' \
                'planner, and response source) will automatically kill this listener.'
    extra_info = """"""

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Autonomous')):
            if await self._is_unauth_process_detected(op) and self._is_unauth_process_killed(op):
                return True
        return False
