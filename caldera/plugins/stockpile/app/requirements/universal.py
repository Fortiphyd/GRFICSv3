from typing import List

from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link

from plugins.stockpile.app.requirements.base_requirement import BaseRequirement


class Requirement(BaseRequirement):

    async def enforce(self, link, operation):
        """
        Given a link and the current operation, check that all facts of a specified type in the
        operation have a specified edge.
        :param link
        :param operation
        :return: True if it complies, False if it doesn't
        """
        facts = await operation.all_facts()
        matching_facts = [fact for fact in facts if fact.trait == self.enforcements['source'] and
                                                    link.paw in fact.collected_by]
        matching_edges = [fact for fact in matching_facts if self._in_relationship_substring(self.enforcements['edge'], fact.relationships)]
        fulfilled = len(matching_facts) == len(matching_edges)

        return fulfilled

    def _in_relationship_substring(self, key: str, relationships: List[str]):
        return any(key in string for string in relationships)
