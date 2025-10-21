from plugins.stockpile.app.requirements.base_requirement import BaseRequirement
from app.utility.base_service import BaseService


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, ensure the ability will only run if the
        agent with the given ID/PAW is listed in the Agents tab on the Caldera Server GUI.
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        agent_paws = [agent.paw for agent in BaseService.get_service('data_svc').ram['agents']]
        for uf in link.used:
            # Remove the "@" character if it appears in the given fact
            # In order to accomodate the Lightneuron implant ID
            if uf.value.replace("@", "") in agent_paws:
                return True
        return False
