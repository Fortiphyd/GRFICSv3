import asyncio


class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['initial_access', 'defense_evasion', 'command_and_control', 'discovery', 'execution',
                              'credential_access', 'privilege_escalation', 'persistence', 'lateral_movement',
                              'collection', 'exfiltration', 'impact']
        self.next_bucket = 'initial_access'   # set first, bucket to execute
        self.current_length = 0

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def do_bucket(self, bucket):
        await self.planning_svc.exhaust_bucket(self, bucket, self.operation)

    async def initial_access(self):
        await self.do_bucket('initial-access')
        self.next_bucket = await self.planning_svc.default_next_bucket('initial_access', self.state_machine)

    async def execution(self):
        await self.do_bucket('execution')
        self.next_bucket = await self.planning_svc.default_next_bucket('execution', self.state_machine)

    async def persistence(self):
        await self.do_bucket('persistence')
        self.next_bucket = await self.planning_svc.default_next_bucket('persistence', self.state_machine)

    async def privilege_escalation(self):
        await self.do_bucket('privilege-escalation')
        self.next_bucket = await self.planning_svc.default_next_bucket('privilege_escalation', self.state_machine)

    async def defense_evasion(self):
        await self.do_bucket('defense-evasion')
        self.next_bucket = await self.planning_svc.default_next_bucket('defense_evasion', self.state_machine)

    async def credential_access(self):
        await self.do_bucket('credential-access')
        self.next_bucket = await self.planning_svc.default_next_bucket('credential_access', self.state_machine)

    async def discovery(self):
        await self.do_bucket('discovery')
        self.next_bucket = await self.planning_svc.default_next_bucket('discovery', self.state_machine)

    async def lateral_movement(self):
        await self.do_bucket('lateral-movement')
        self.next_bucket = await self.planning_svc.default_next_bucket('lateral_movement', self.state_machine)

    async def collection(self):
        await self.do_bucket('collection')
        self.next_bucket = await self.planning_svc.default_next_bucket('collection', self.state_machine)

    async def command_and_control(self):
        await self.do_bucket('command-and-control')
        self.next_bucket = await self.planning_svc.default_next_bucket('command_and_control', self.state_machine)

    async def exfiltration(self):
        await self.do_bucket('exfiltration')
        self.next_bucket = await self.planning_svc.default_next_bucket('exfiltration', self.state_machine)

    async def impact(self):
        await self.do_bucket('impact')
        if len(self.operation.chain) == self.current_length:  # check to see if we've done anything new recently
            if self.operation.auto_close:  # we aren't making any further forward progress, and we should close
                self.next_bucket = None
            else:  # we aren't making any further forward progress, but let's wait a bit and see if that changes
                await asyncio.sleep(180)  # Sleep for a while before we enter the flow loop again
                self.planning_svc.log.debug('[buckets] Ran out of things to do for the moment. Sleeping for a bit.')
                self.next_bucket = 'initial_access'
        else:
            self.current_length = len(self.operation.chain)
            self.next_bucket = await self.planning_svc.default_next_bucket('impact', self.state_machine)
