from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, ensure that the link does not result in lateral movement onto hosts that
        have already been compromised. The enforcement mechanism is defined per ability
        with the abilities enforcement mechanism
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        all_hostnames = [agent.host.lower() for agent in await operation.active_agents()]
        for uf in link.used:
            if self.enforcements['source'] == uf.trait:
                target_name = uf.value.split('.')[0].lower()
                if target_name in all_hostnames or any(target_name in h for h in all_hostnames):
                    return False
        return True
