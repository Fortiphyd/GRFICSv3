from app.utility.base_world import BaseWorld


class LogicalPlanner:
    def __init__(self, operation, planning_svc, stopping_conditions=(), filtered_groups_by_ability=None):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['fetch_and_run_links']
        self.next_bucket = 'fetch_and_run_links'   # repeat this bucket until we run out of links.
        self.filtered_groups_by_ability = filtered_groups_by_ability if filtered_groups_by_ability else dict()
        self.pending_links = []
        self.current_ability_index = 0
        self.log = BaseWorld.create_logger('group_filtered_planner')

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def fetch_and_run_links(self):
        links_to_use = await self._fetch_links()
        if links_to_use:
            # Each agent will run the next available step.
            self.log.debug('Applying %d links', len(links_to_use))
            links_to_wait_for = [await self.operation.apply(link) for link in links_to_use]
            await self.operation.wait_for_links_completion(links_to_wait_for)
        else:
            self.log.debug('No more links to run.')
            self.next_bucket = None

    async def _fetch_links(self):
        # If we have no pending links, go to the next ability in the adversary profile.
        # Determine which agents can run the ability based on filtered_groups_by_activity and then generate
        # the pool of links for just that ability.
        # If the ability does not generate any runnable links, iterate through the
        # atomic ordering until we find an ability that does generate links.
        while not self.pending_links:
            if self.current_ability_index >= len(self.operation.adversary.atomic_ordering):
                return []
            ability_id = self.operation.adversary.atomic_ordering[self.current_ability_index]
            self.pending_links = await self._get_pending_links(ability_id)
            self.current_ability_index += 1
        return self._fetch_from_pending_links()

    async def _get_pending_links(self, ability_id):
        valid_agents = self._get_valid_agents_for_ability(ability_id)
        potential_links = []
        for agent in valid_agents:
            potential_links += await self._get_links(agent=agent)
        return [link for link in potential_links if link.ability.ability_id == ability_id]

    def _fetch_from_pending_links(self):
        """Return at most one link per agent. Any link that gets assigned will be removed from self.pending_links."""
        assigned_agent_paws = set()
        links_to_use = []
        unassigned_links = []
        for link in self.pending_links:
            if link.paw not in assigned_agent_paws:
                assigned_agent_paws.add(link.paw)
                links_to_use.append(link)
            else:
                # Agent has already been assigned a link from this pool
                unassigned_links.append(link)
        self.pending_links = unassigned_links
        return links_to_use

    def _get_valid_agents_for_ability(self, ability_id):
        if ability_id not in self.filtered_groups_by_ability:
            return self.operation.agents
        valid_agents = []
        for agent in self.operation.agents:
            if agent.group in self.filtered_groups_by_ability.get(ability_id, []):
                valid_agents.append(agent)
        return valid_agents

    async def _get_links(self, agent=None):
        return await self.planning_svc.get_links(operation=self.operation, agent=agent)
