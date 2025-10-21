from app.utility.base_world import BaseWorld
from plugins.training.app.c_flag import Flag


class AutonomousBlue3(Flag):
    name = 'Suspicious URL in mail'
    challenge = 'Use the \'mail\' utility to send an email to a user on the Linux or Darwin machine. Spoof the ' \
                'sender address to be an email address with a fake malicious domain. The autonomous defender should ' \
                'find this URL and add an entry to the /etc/hosts file, redirecting the URL to localhost.'
    extra_info = """"""

    async def verify(self, services):
        async def is_url_found(operation):
            return 'remote.suspicious.url' in [f.trait for f in await operation.all_facts()] \
                   and operation.ran_ability_id('1226f8ec-e2e5-4311-88e7-378c0e5cc7ce')

        def is_url_inoculated(operation):
            return operation.ran_ability_id('2ca64acd-dc12-4cc8-b78a-6a182508a50b')

        for op in await services.get('data_svc').locate('operations',
                                                        match=dict(access=BaseWorld.Access.BLUE,
                                                                   name='Blue Autonomous')):
            if await is_url_found(op) and is_url_inoculated(op):
                return True
        return False
