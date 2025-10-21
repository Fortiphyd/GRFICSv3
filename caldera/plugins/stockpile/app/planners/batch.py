class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['batch']
        self.next_bucket = 'batch'   # set first (and only) bucket to execute

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def batch(self):
        links = await self._get_links()
        while links:
            link_ids = [await self.operation.apply(link) for link in links]
            await self.operation.wait_for_links_completion(link_ids)
            # new links may be available now (e.g. requirements met)
            links = await self._get_links()
        self.next_bucket = None

    async def _get_links(self):
        return await self.planning_svc.get_links(operation=self.operation)
