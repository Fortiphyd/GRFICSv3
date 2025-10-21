from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


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
                    if self.is_valid([f for f in link.used if f != uf], r):
                        return True
        return False

    def is_valid(self, used_facts, relationship):
        """
        Checks if the used facts for a link match with the list of known fact relationships
        :param used_facts:
        :param relationship:
        :return: True if there is a match, False if not
        """
        if not self._check_edge(relationship.edge):
            return False
        if 'target' in self.enforcements.keys():
            for fact in used_facts:
                if self._check_fuzzy(relationship.target, fact):
                    return True
            return False
        return True

    @staticmethod
    def _check_fuzzy(target, match):
        if target.trait == match.trait:
            if target.value.startswith(match.value) or match.value.startswith(target.value):
                return True
            t1 = target.value.split('\\')
            m1 = match.value.split('\\')
            if len(t1) == len(m1) and len(m1) == 2:
                if (t1[0] in match.value and t1[1] in match.value) or (m1[0] in target.value and m1[1] in target.value):
                    return True
        return False
