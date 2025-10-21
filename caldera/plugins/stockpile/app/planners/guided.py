import collections
import copy
import re
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.secondclass.c_executor import Executor
from app.objects.secondclass.c_goal import Goal
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_link import Link
from app.service.planning_svc import PlanningService
from app.utility.base_planning_svc import BasePlanningService


FACT_REGEX = BasePlanningService.re_variable  # Matches text contained inside #{ }
LIMIT_REGEX = (
    BasePlanningService.re_trait
)  # Matches all text prior to '[', used to determine whether a trait contains a limit or not
EXHAUSTION_KEY = 'exhaustion'

DEFAULT_HALF_LIFE_PENALTY = 4
DEFAULT_HALF_LIFE_GAIN = 2
DEFAULT_GOAL_ACTION_DECAY = 2
DEFAULT_GOAL_WEIGHT = 1
DEFAULT_FACT_SCORE_WEIGHT = 0
DEFAULT_EXHAUSTION_GOAL_COUNT = 1

DEBUG_ATTACK_GRAPH_FILEPATH = 'guided_attack_graph.pdf'


class LogicalPlanner:
    """
    The Guided planner makes use of distance to goals in a dependency graph to select the optimal next action.

    On operation start:
    1. Identify the set of goal fact types that we're looking for

    2. Compute the distance score for each ability
        -- Defined as the shortest distance -- measured in actions -- between each ability and a goal fact type
            -- To compute this, we usually have to compute (in some way) the underlying attack graph
            -- If an action has two paths to a goal fact type, choose the /shortest/
            -- An action that immediately leads to a goal fact type gets a score of 0
            -- An action that leads to an action that leads to a goal fact type gets a score of 1, etc.
        -- Distance scores should be /reversed/ so that "goal actions" -- i.e., those initially with 0 -- get the /biggest/ score
            -- Compute the distance score as per the step above and find the ability with the largest score (i.e., the longest path to a goal)
            -- Set each ability's updated score the "abs(cur_score - max_score)" to reverse it

    3. Initialize needed variables:
        -- half_life_penalty: how much we penalize an action for not being helpful
        -- half_life_gain: how much we passively increase each action's score
        -- goal_action_decay: how much we deprioritize a specific goal action
            -- Note: we define a "goal action" as an action that leads to a goal fact type
        -- goal_weight: how much we "weigh" the action's distance to a goal
        -- fact_score_weight: how much we weigh the action's constituent facts
        -- absolute_distance: the distance table computed in step 2
        -- effective_distance: will store the /decaying/ distance, but is initialized to be equal to absolute distance
            -- Sometimes we call this "last distance"


    On action selection:

    4. Get all available links

    5. Select the action with the highest score -- execute it and parse results
        -- An action's score is the weighted sum of its fact score + its distance score
        -- score(A) = goal_weight * effective_distance(A) + fact_score_weight * fact_score(A)

    6. Penalize the last action executed if it did not bring us closer to the goal
        -- If the last action was not a goal action:
            -- Find the current max reward by iterating through each ability from step 5 and recording the /absolute_distance/ of that ability
            -- If 'max_reward > absolute_distance(last_action)' that means that we're now closer to the goal
                -- For this case, we "reset" the effective distance of the last action: 'effective_distance(last_action) = absolute_distance(last_action)'
            -- Otherwise, we didn't make progress, so we need to penalize the last action
                -- To do this, we do: effective_distance(last_action) = effective_distance(last_action)/half_life_penalty
        -- If the last action was a goal action:
            -- We want to "decentivize" this action to avoid local optima (i.e., so it doesn't always execute the same goal action repeatedly and it pursues other goals)
            -- Computed as: effective_distance(A) = max_value - 1 + (effective_distance(A) + 1 - max_value)/goal_action_decay
            -- Note that max_value is defined as the largest value in absolute_distance
            -- What this does is this makes sure that the goal action's score is always between (max_value) and (max_value - 1) so it will /always/ be prioritized over normal actions

    7. Determine if we've satisfied our goals:
        7a) If we've now satisfied all of our goals, terminate
        7b) If we've satisfied a goal, but other goals remain, re-run step 2, reset effective_distance, and return to step 4
        7c) If we haven't made any changes to our goals, return to step 4
    """

    def __init__(
        self,
        operation: Operation,
        planning_svc: PlanningService,
        stopping_conditions: List[Fact] = (),
        half_life_penalty: float = DEFAULT_HALF_LIFE_PENALTY,
        half_life_gain: float = DEFAULT_HALF_LIFE_GAIN,
        goal_action_decay: float = DEFAULT_GOAL_ACTION_DECAY,
        goal_weight: float = DEFAULT_GOAL_WEIGHT,
        fact_score_weight: float = DEFAULT_FACT_SCORE_WEIGHT,
        exhaustion_goal_count: int = DEFAULT_EXHAUSTION_GOAL_COUNT,
        debug: bool = False,
    ):
        """
        :param operation:
        :param planning_svc:
        :param stopping_conditions:
        :param half_life_penalty: Weight to penalize an action for not being helpful.
        :param half_life_gain: Weight to passively increase each action's score.
        :param goal_action_decay: Weight to deprioritize a specific goal action.
        :param goal_weight: Weight for the action's distance to a goal.
        :param fact_score_weight: Weight for the action's constituent facts.
        :param exhaustion_goal_count: Number of times to achieve a goal when using exhaustion objective.
        """
        self.operation = operation
        self.planning_svc = planning_svc
        self.data_svc = planning_svc.get_service('data_svc')
        self.goals = operation.objective.goals
        self.ability_ids = operation.adversary.atomic_ordering

        self.half_life_penalty = half_life_penalty
        self.half_life_gain = half_life_gain
        self.goal_action_decay = goal_action_decay
        self.goal_weight = goal_weight
        self.fact_score_weight = fact_score_weight
        self.exhaustion_goal_count = exhaustion_goal_count
        self.last_action = None
        self.goal_actions = set()
        self.debug = debug

        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['guided']
        self.next_bucket = 'guided'

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def guided(self):
        await self.execute_subop(ability_ids=self.ability_ids, goals=self.goals)

    async def execute_subop(
        self, ability_ids: List[str], agent: Agent = None, goals: List[Goal] = []
    ):
        """
        :param ability_ids: List of ability IDs to plan with.
        :param agent: Agent to focus planning on. If no agent is provided, planning will focus on all agents available in the operation.
        :param goals: List of Goal objects to plan towards. Providing an empty list or an Exhaustion goal will cause the planner to infer goals from the ability's dependency graph.
        """
        attack_graph = await self._build_attack_graph(ability_ids, agent)
        if self.debug:
            await self._show_attack_graph(attack_graph)

        if len(goals) == 0 or goals[0].target == EXHAUSTION_KEY:
            planner_goals = await self._create_terminal_goals(attack_graph)
        else:
            planner_goals = goals[:]

        absolute_distance_table = await self._build_distance_table(
            attack_graph, goals=planner_goals
        )
        effective_distance_table = copy.deepcopy(absolute_distance_table)

        goal_links = await self._get_goal_links(absolute_distance_table, agent=agent)
        while len(planner_goals) > 0 and len(goal_links) > 0:
            tasked_links = await self._task_best_action(
                goal_links, effective_distance_table, ability_ids
            )

            await self.operation.wait_for_links_completion([link.id for link in tasked_links])

            current_goal_count = len(planner_goals)
            planner_goals = await self._update_goals(current_goals=planner_goals)
            if len(planner_goals) < current_goal_count:
                (
                    absolute_distance_table,
                    effective_distance_table,
                ) = await self._handle_goal_achieved(attack_graph, goals=planner_goals)
            else:
                effective_distance_table = await self._handle_no_goal_achieved(
                    absolute_distance_table, effective_distance_table, goal_links
                )
            goal_links = await self._get_goal_links(
                absolute_distance_table, agent=agent
            )

        self.planning_svc.log.debug(
            'No more links available or all goals satisfied, planner complete.'
        )
        self.next_bucket = None

    """ PRIVATE """

    async def _build_attack_graph(
        self, ability_ids: List[str], agent: Agent
    ) -> nx.DiGraph:
        """
        Produces a directed graph that includes nodes for each ability, and nodes of each input and output fact
        of those abilities.
        """
        attack_graph = nx.DiGraph()
        for ability_id in ability_ids:
            for ability in await self.data_svc.locate(
                'abilities', dict(ability_id=ability_id)
            ):
                if agent:
                    attack_graph = await self._output_fact_edges(
                        ability, attack_graph, agent
                    )
                    attack_graph = await self._input_fact_edges(
                        ability, attack_graph, agent
                    )
                else:
                    for operation_agent in self.operation.agents:
                        attack_graph = await self._output_fact_edges(
                            ability, attack_graph, operation_agent
                        )
                        attack_graph = await self._input_fact_edges(
                            ability, attack_graph, operation_agent
                        )
                attack_graph = await self._requirement_edges(ability, attack_graph)
        return attack_graph

    async def _show_attack_graph(self, g):
        """DEBUG function -
        convert graph to human readable/useful nodes and pop-up window

        WARN: matplotlib will create a deluge of debug messages.
        """
        from pathlib import Path
        import matplotlib.pyplot as plt

        PDF_FILE = Path.home().joinpath(DEBUG_ATTACK_GRAPH_FILEPATH)
        g_c = nx.DiGraph()
        for e in g.edges:
            s, t = e
            if not isinstance(s, str):
                s = '{}:{}'.format(s.ability_id[:7] + '..', s.name)
            if not isinstance(e[1], str):
                t = '{}:{}'.format(t.ability_id[:7] + '..', t.name)
            g_c.add_edge(s, t)
        pos = nx.spring_layout(g_c, k=0.60, iterations=30)
        nx.draw(
            g_c,
            pos=pos,
            with_labels=True,
            node_color='red',
            edge_color='black',
            font_weight='bold',
        )
        plt.savefig(PDF_FILE)

    async def _output_fact_edges(
        self, ability: Ability, graph: nx.DiGraph, agent: Agent
    ) -> nx.DiGraph:
        """
        Adds output facts to a directed graph based on the parserconfigs included in an ability.
        """
        executor = await agent.get_preferred_executor(ability)
        if self._is_invalid_executor(executor):
            return graph
        for parser in executor.parsers:
            for parserconfig in parser.parserconfigs:
                graph.add_edge(ability, parserconfig.source)
                if parserconfig.target:
                    graph.add_edge(ability, parserconfig.target)
                if parserconfig.edge:
                    graph.add_edge(ability, parserconfig.edge)
        return graph

    async def _input_fact_edges(
        self, ability: Ability, graph: nx.DiGraph, agent: Agent
    ) -> nx.DiGraph:
        """
        Adds input facts to a directed graph based on the facts present in a command template.
        """

        def add_to_graph(fact: Fact):
            if fact not in list(Agent.RESERVED):
                graph.add_edge(fact, ability)

        executor = await agent.get_preferred_executor(ability)
        if self._is_invalid_executor(executor):
            return graph
        for fact in re.findall(FACT_REGEX, executor.test):
            nonlimited = re.search(LIMIT_REGEX, fact)
            if nonlimited:
                add_to_graph(nonlimited.group(0).split('#{')[-1])
            else:
                add_to_graph(fact)
        return graph

    async def _requirement_edges(self, ability: Ability, graph: nx.Graph) -> nx.DiGraph:
        """
        Adds requirement information to a directed graph.
        """
        for requirement in ability.requirements:
            for relationship in requirement.relationship_match:
                graph.add_edge(relationship['source'], ability)
                if relationship.get('target', None):
                    graph.add_edge(relationship['source'], relationship['target'])
                    graph.add_edge(relationship['target'], ability)
        return graph

    async def _create_terminal_goals(self, attack_graph: nx.DiGraph) -> List[Goal]:
        """
        Infers goals based on which nodes in a directed graph have an outward degreee of zero.
        """
        terminal_nodes = [
            node for node, degree in attack_graph.out_degree() if degree == 0
        ]
        aggregated_goals = collections.Counter(terminal_nodes)
        goals = [
            Goal(target=trait, operator='*', count=count * self.exhaustion_goal_count)
            for trait, count in aggregated_goals.items()
        ]
        return goals

    async def _build_distance_table(
        self, graph: nx.DiGraph, goals: List[Goal]
    ) -> Dict[str, float]:
        """
        Constructs a table of shortest distance from each ability to one of the goals. The weights get
        inverted, so the highest score in the table is the closest action to a goal.
        """
        ability_distances = dict()
        self.goal_actions = set()
        max_dist = 0

        for goal in goals:
            shortest_path = nx.shortest_path(graph, target=goal.target)

            for node, path in shortest_path.items():
                if not isinstance(node, Ability):
                    continue

                filtered_path = [n for n in path if isinstance(n, Ability)]
                path_distance = len(filtered_path)

                if path_distance == 1:
                    self.goal_actions.add(node.ability_id)

                if path_distance > max_dist:
                    max_dist = path_distance

                if (
                    node.ability_id in ability_distances
                    and path_distance > ability_distances[node.ability_id]
                ):
                    continue

                ability_distances[node.ability_id] = path_distance

        for ab, length in ability_distances.items():
            ability_distances[ab] = abs(length - max_dist) + 1

        return ability_distances

    async def _handle_goal_achieved(
        self, attack_graph: nx.DiGraph, goals: List[Goal] = None
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Rebuilds the distance table based on a revised set of goals.
        """
        absolute_distance_table = await self._build_distance_table(
            attack_graph, goals=goals
        )
        effective_distance_table = copy.deepcopy(absolute_distance_table)
        return absolute_distance_table, effective_distance_table

    async def _handle_no_goal_achieved(
        self,
        absolute_dist_table: Dict[str, float],
        effective_dist_table: Dict[str, float],
        goal_links: List[Goal],
    ):
        """
        Penalizes the weights in the current effective distance table to keep the planner out of endless loops.
        """
        executable_link_max_val = max(
            absolute_dist_table[l.ability.ability_id] for l in goal_links
        )
        last_action_effective_score = effective_dist_table[self.last_action.ability_id]
        last_action_absolute_score = absolute_dist_table[self.last_action.ability_id]
        effective_dist_table[
            self.last_action.ability_id
        ] = self._apply_effective_distance_penalty(
            last_action_effective_score,
            last_action_absolute_score,
            executable_link_max_val,
        )

        for ability_id, score in effective_dist_table.items():
            effective_dist_table[ability_id] = (
                score
                + float(absolute_dist_table[ability_id] - score) / self.half_life_gain
            )
        return effective_dist_table

    def _apply_effective_distance_penalty(
        self, effective_score: float, absolute_score: float, max_value: float
    ) -> float:
        """
        Calculates the new effective distance for the last action performed.
        """
        if self.last_action.ability_id in self.goal_actions:
            new_distance = self._calculate_goal_action_penalty(
                max_value, effective_score
            )
        else:
            new_distance = self._calculate_non_goal_action_penalty(
                max_value, absolute_score, effective_score
            )

        return new_distance

    def _calculate_goal_action_penalty(self, max_value, effective_score):
        """
        Calculates new effective distance for a goal action for use when no goal was achieved.
        """
        return (
            max_value
            - 1
            + float(effective_score + 1 - max_value) / self.goal_action_decay
        )

    def _calculate_non_goal_action_penalty(
        self, max_value, absolute_score, effective_score
    ):
        """
        Calculates new effective distance for a non-goal action for use when no goal was achieved.
        """
        if max_value > abs(absolute_score):
            new_distance = absolute_score
        else:
            new_distance = float(effective_score) / self.half_life_penalty

        return new_distance

    async def _get_goal_links(
        self, absolute_distance_table: Dict[str, float], agent: Agent = None
    ) -> List[Link]:
        """
        Produces all links for abilities that are present in the absolute distance table.
        """
        links = await self.planning_svc.get_links(self.operation, agent=agent)
        return [
            link for link in links if link.ability.ability_id in absolute_distance_table
        ]

    async def _task_best_action(
        self,
        agent_links: List[Link],
        link_distance_table: Dict[str, float],
        ability_ids: List[str],
    ) -> Link:
        """
        Produces the best available link based on the current distance table. The method also applies links
        that support the chosen link, but that do not actively work towards the goal.
        """
        weighted_scores = [
            (
                (
                    link_distance_table[link.ability.ability_id] * self.goal_weight
                    + link.score * self.fact_score_weight
                ),
                link,
            )
            for link in agent_links
        ]
        keys_to_sort = [
            (-distance_to_goal, -link.score, link_index, link)
            for link_index, (distance_to_goal, link) in enumerate(weighted_scores)
        ]
        sorted_links = [link for _, _, _, link in sorted(keys_to_sort)]
        link_to_execute = sorted_links[0]

        supporting_links = await self._get_supporting_links(
            link_to_execute, ability_ids
        )
        for supporting_link in supporting_links:
            await self.operation.apply(supporting_link)
        await self.operation.apply(link_to_execute)
        self.last_action = link_to_execute.ability
        return [link_to_execute, *supporting_links]

    async def _get_supporting_links(
        self, link: Link, ability_ids: List[str]
    ) -> List[Link]:
        """
        This method is a quick fix that ideally should be resolved by improvements to abilities at some point in the future.
        It's here to capture orphaned abilities that do not have any output facts. Within the dependency graph, they would
        look like single nodes that are not directly connected to any other components. It is still possible given the way
        that some abilities are implemented that some of these orphaned abilities are expected to be run before others even
        though there is not a fact dependency between them. This method gets around this by selecting all links with no
        output facts that are earlier in the atomic ordering than the currently chosen link. This guarantees that all
        possible dependent actions are taken prior to the chosen action.
        """

        async def has_output_facts(ability: Ability, agent: Agent):
            executor = await agent.get_preferred_executor(ability)
            if not executor:
                return False
            for parser in executor.parsers:
                if parser.parserconfigs:
                    return True
            return False

        if self.last_action:
            last_ability_index = np.where(self.last_action.ability_id == np.array(ability_ids))[0][0]
        else:
            last_ability_index = 0
        link_ability_index = np.where(link.ability.ability_id == np.array(ability_ids))[0][0]

        agent = (await self.data_svc.locate('agents', match=dict(paw=link.paw)))[0]
        links = await self.planning_svc.get_links(self.operation, agent=agent)
        connecting_abilities = ability_ids[last_ability_index:link_ability_index]
        connecting_abilities = await self.data_svc.locate(
            'abilities', match=dict(ability_id=tuple(connecting_abilities))
        )
        connecting_abilities = [
            ability
            for ability in connecting_abilities
            if not await has_output_facts(ability, agent)
        ]
        supporting_links = [
            l for ability in connecting_abilities for l in links if l.ability == ability
        ]

        return supporting_links

    async def _update_goals(self, current_goals: List[Goal]) -> List[Goal]:
        """
        Removes goals from the set that have been successfully accomplished.
        """
        remaining_goals = []
        for goal in current_goals:
            if goal.satisfied(await self.operation.all_facts()):
                self.planning_svc.log.debug(
                    f'Goal {goal.target} {goal.operator} {goal.value} accomplished!'
                )
            else:
                remaining_goals.append(goal)
        return remaining_goals
    
    def _is_invalid_executor(self, executor: Executor):
        return not executor or executor.command is None
