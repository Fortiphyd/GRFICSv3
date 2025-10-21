from plugins.response.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, check if the link's used fact combination complies
        with the abilities enforcement mechanism
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        relationships = await operation.all_relationships()
        for uf in link.used:
            if self.enforcements['source'] == uf.trait:
                for r in self._get_relationships(uf, relationships):
                    if self.is_valid_relationship([f for f in link.used if f != uf], r):
                        return True
        return False
