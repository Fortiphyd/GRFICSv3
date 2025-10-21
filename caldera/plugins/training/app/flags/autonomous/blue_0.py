from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class AutonomousBlue0(Flag):
    name = 'Enable Autonomous Operation'
    challenge = 'Start an autonomous blue operation using the Incident Responder defender profile. Ensure that the ' \
                'batch planner is used. Name this operation exactly \'Blue Autonomous\'. Keep this operation open ' \
                'to successfully complete the flags for this badge.'
    extra_info = """"""

    async def verify(self, services):
        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE, name='Blue Autonomous')):
            if op.adversary.adversary_id == '7e422753-ad7a-4401-bc8b-b12a28e69c25' and op.planner.name == 'batch':
                return True
        return False
