from plugins.training.app.c_flag import Flag


class AgentsBlue0(Flag):
    name = 'Red agent - *nix'
    challenge = 'Deploy a red agent on a Linux or Mac/Darwin machine with a group named exactly \'cert-nix\'. ' \
                'This agent will be used in later challenges.'
    extra_info = """"""

    async def verify(self, services):
        for agent in await services.get('data_svc').locate('agents'):
            if agent.platform in ['linux', 'darwin'] and agent.group == 'cert-nix':
                return True
        return False
