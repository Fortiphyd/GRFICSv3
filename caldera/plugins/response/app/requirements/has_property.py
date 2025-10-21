from plugins.response.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, check if the link's used fact has the specified property.
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        relationships = await operation.all_relationships()
        for uf in link.used:
            if self.enforcements['source'] == uf.trait:
                for r in self._get_relationships(uf, relationships):
                    if r.edge == 'has_property' and r.target.trait == self.enforcements['target']:
                        return True
        return False
