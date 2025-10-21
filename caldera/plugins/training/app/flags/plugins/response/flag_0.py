from plugins.training.app.c_flag import Flag


class PluginsResponseFlag0(Flag):
    name = 'Blue agent'

    challenge = (
        'Log in as a blue user and deploy a new blue agent. The agent should successfully beacon back to '
        'this server instance. Blue agents should be run with elevated privileges.'
    )

    extra_info = (
        'Most Endpoint Detection and Response products use agents that are installed on the endpoints that '
        'need to be protected. Sandcat can function as Caldera\'s Blue agent too.'
    )

    async def verify(self, services):
        agents = await services.get('data_svc').locate('agents')
        return True if any(agent.group == 'blue' for agent in agents) else False
