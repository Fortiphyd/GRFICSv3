from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, ensure will only run if the agent with the given ID/PAW is alive.
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        agent_paws = [agent.paw for agent in await operation.active_agents()]
        for uf in link.used:
            if uf.value in agent_paws:
                return True
        return False
