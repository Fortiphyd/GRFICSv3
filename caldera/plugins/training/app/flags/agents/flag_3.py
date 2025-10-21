from plugins.training.app.c_flag import Flag


class AgentsFlag3(Flag):
    name = 'Update agent'
    challenge = 'Pick any agent and change the group and sleep (min and max) values associated to it.'
    extra_info = (
        'If an agent\'s beacon time is too regular - or predictable - it runs a higher chance of getting '
        'caught. It is advisable to select a random time range instead of a hard-coded interval. Usually, an adversary '
        'will aim to have multiple agents deployed on a host, with some frequent beacon times and some infrequent. '
        'This gives them a backup in case one gets detected.'
    )

    async def verify(self, services):
        for a in await services.get('data_svc').locate('agents'):
            if a.group != 'red' and a.sleep_min != 30 and a.sleep_max != 60:
                return True
        return False
