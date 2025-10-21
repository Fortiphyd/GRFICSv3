from plugins.training.app.c_flag import Flag


class AgentsBlue1(Flag):
    name = 'Blue agent - *nix'
    challenge = 'Deploy a blue agent on a Linux or Mac/Darwin machine. Ensure that this agent has ELEVATED ' \
                'privileges. This agent will be used in later challenges.'
    extra_info = """"""

    async def verify(self, services):
        for agent in await services.get('data_svc').locate('agents'):
            if agent.platform in ['linux', 'darwin'] and agent.group == 'blue' and agent.privilege == 'Elevated':
                return True
        return False
