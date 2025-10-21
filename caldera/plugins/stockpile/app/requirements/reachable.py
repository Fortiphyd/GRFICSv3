from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a mounting link, verify the selected agent can reach the target.
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        relationships = await operation.all_relationships()
        for uf in link.used:
            if self.enforcements['source'] == uf.trait:
                for r in self._get_relationships(uf, relationships):
                    links = [x for x in operation.chain if r in x.relationships]
                    host = links[0].host
                    if r.source.value == uf.value:
                        if link.host == host:  # running on the host that created this relationship
                            return True
        return False
