from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link, check if any of the used facts must comply with paw provenance requirements
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        for uf in link.used:
            if self.enforcements['source'] == uf.trait and link.paw in uf.collected_by:
                return True
        return False
