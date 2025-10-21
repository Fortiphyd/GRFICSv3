class LogicalPlanner:
    """
    The look ahead planner decides what abilities to use based on anticipated
    future rewards. It takes as input a table of ability rewards, a depth
    parameter, and a discount factor. The depth parameter effectively controls
    the "look-ahead" for the planner as it's scoring each action, and the
    discount factor controls how the planner weighs future rewards. (The
    planner also only executes one action (i.e. link) at a time, even if
    numerous agents).

    Before describing the algorithm, some notation:

    - Let g be the discount factor. This is defined globally. Default this to 0.9.
    - Let d be the look-ahead depth. This is defined globally. Default this to 3.
    - Let the set of abilities be A.
    - Define a function E : A x P(A) to be a function that maps each ability a in
      A to the set of abilities that follow a.
    - We say that ability B follows ability A if there is a parser for A that
      produces a fact that's input for B. Tying into language from above, we might
      have an example where: E(a) = {b}.
    - Let R : A x N be our reward table, mapping each ability to its immediate reward.

    Pseudo-code of future reward calculation:

    future_reward(current_ability, current_depth):
        if current_depth > d:
            return 0
        future_rewards = []
        for action in E(current_ability):
            future_rewards.append(future_reward(action, current_depth + 1))
        return R(current_ability) * g^(current_depth) + max(future_rewards)

    """

    DEPTH = 3
    DISCOUNT = 0.9
    DEFAULT_REWARD = 1

    def __init__(
        self,
        operation,
        planning_svc,
        ability_rewards=None,
        depth=DEPTH,
        discount=DISCOUNT,
        default_reward=DEFAULT_REWARD,
        stopping_conditions=(),
    ):
        """
        :param operation:
        :param planning_svc:
        :param ability_rewards:
        :param depth:
        :param discount:
        :param default_reward:
        :param stopping_conditions:
        """
        self.operation = operation
        self.planning_svc = planning_svc
        self.data_svc = planning_svc.get_service('data_svc')
        self.ability_rewards = ability_rewards or {}
        self.depth = depth
        self.discount = discount
        self.default_reward = default_reward
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['look_ahead']
        self.next_bucket = 'look_ahead'  # repeat this bucket until we run out of links

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def look_ahead(self):
        # Get highest scoring link over all agents
        agent_link_rewards = []
        for agent in self.operation.agents:
            ao = self.operation.adversary.atomic_ordering
            abilities = await self.data_svc.locate(
                'abilities', match=dict(ability_id=tuple(ao))
            )
            abilities = await agent.capabilities(abilities)

            cand_links = await self.planning_svc.get_links(
                self.operation, agent=agent, trim=True
            )

            ability_rewards = []
            for ability in abilities:
                ability_rewards.append(
                    (
                        ability.ability_id,
                        await self._future_reward(agent, ability, abilities, 0),
                    )
                )

            next_link_and_reward = None
            ability_rewards = sorted(ability_rewards, key=lambda r: r[1], reverse=True)
            for ability_reward in ability_rewards:
                ability_links = [
                    link
                    for link in cand_links
                    if link.ability.ability_id == ability_reward[0]
                ]
                if ability_links:
                    next_link_and_reward = (ability_links[0], ability_reward[1])
                    break

            if next_link_and_reward:
                agent_link_rewards.append(next_link_and_reward)

        # Now we have the highest scoring link for each agent,
        # select the link with the highest score from all the
        # agents and push to agent
        if agent_link_rewards:
            agent_link_rewards = sorted(
                agent_link_rewards, key=lambda r: r[1], reverse=True
            )
            link_id = await self.operation.apply(agent_link_rewards[0][0])
            await self.operation.wait_for_links_completion([link_id])
        else:
            self.next_bucket = None

    async def _future_reward(self, agent, current_ability, abilities, current_depth):
        """Calculate the reward for current ability
        :param agent:
        :param current_ability:
        :param abilities:
        :param current_depth:
        :return: ability reward value
        """
        if current_depth > self.depth:
            return 0
        abilities = set(abilities) - set([current_ability])
        future_rewards = [0]
        abilities_that_follow = await self._abilities_that_follow(
            agent, current_ability, abilities
        )
        for ability in abilities_that_follow:
            future_rewards.append(
                await self._future_reward(agent, ability, abilities, current_depth + 1)
            )
        reward = round(
            self.ability_rewards.get(current_ability.ability_id, self.default_reward)
            * (self.discount**current_depth)
            + max(future_rewards),
            3,
        )
        return reward

    async def _abilities_that_follow(self, agent, current_ability, abilities):
        """Return list of abilities that could follow current ability
        (based on whether the ability's command uses facts that are created/set
        by the current ability)
        :param agent:
        :param current_ability:
        :param abilities:
        :return: list of abilities
        """
        current_executor = await agent.get_preferred_executor(current_ability)
        facts = [
            fact
            for parser in current_executor.parsers
            for cfg in parser.parserconfigs
            for fact in [cfg.source, cfg.target]
            if fact is not None and fact != ''
        ]
        next_abilities = []
        for ability in abilities:
            executor = await agent.get_preferred_executor(ability)
            if executor.command and any(fact in executor.command for fact in facts):
                next_abilities.append(ability)
        return next_abilities
