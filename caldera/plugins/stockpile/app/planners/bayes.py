from typing import List, Dict, Union
from base64 import b64decode

from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.service.planning_svc import PlanningService


UPDATE_AFTER_LINKS = 10  # Frequency with which to update operation/action data used for bayes reasoning. Frequency unit is newly executed links (actions).
FEATURE_NAMES = [  # Features collected per link from operational data
    "Ability_ID",
    "Adversary_ID",
    "Adversary_Name",
    "Agent_Privilege",
    "Agent_Protocol",
    "Command",
    "Executor_Name",
    "Executor_Platform",
    "Host_Architecture",
    "Link_Facts",
    "Number_Facts",
    "Obfuscator",
    "Planner",
    "Status",
    "Trusted_Status",
    "Visibility_Score"
]
HOST_SPECIFIC_FACT_TRAITS = ("host.", "remote.", "file.last.", "domain.user.")


class LogicalPlanner:
    """Bayes Planner
    The planner utilizes past operational history to execute operations while
    prioritizing likelihood of link (action) success. With sufficient local data, NB planner
    runs all operations in order of most to least effective links, while dropping
    links with insufficient likelihood of success.
    The NB Planner recieves the following parameters:
        - min_link_data: the minimum number of past instances of a link (actions) in existing past
        operational data necessary for planner to utilize its probability of success.
        Can be custom set by user in 
        \stockpile\data\planners\48e1a882-1606-4910-8f2d-2352eb80cba2.yml, default is 3.
        - debug: Boolean indicating whether planner should log link selection
        logic in DEBUG level system output. Defaults to False, can also be changed in
        .yml config.
        - delay_execution_links: list of link ids whose execution should be pushed back
        to atomic ordering and treated as insufficient data to improve operation ordering.
        Set in config.
        -  min_prob_link_success: minimum calculated likelihood of success necessary to
        run a link (action). Set in config. Default is 49%
    Algorithm:
        - While there are available link(s) in the operation for live agent(s):
            - If there are link(s) that satisfy minimum operational data settings and 
            minimum link probability of success settings:
                - Execute the link with the highest calculated probability of success
            - Else:
                - If there are remaining link(s) with insufficient past operational data:
                    - Execute next link based on atomic ordering
            - Drop any links that with sufficient past data but insufficient calculated
            probability of success
        - Terminate when out of links or all links have too low likelihood of success
    """

    def __init__(
        self, 
        operation: Operation, 
        planning_svc: PlanningService, 
        min_prob_link_success : float,
        min_link_data: int,
        excluded_trait_prefixes: List[str] = HOST_SPECIFIC_FACT_TRAITS,
        debug: bool = False,
        delay_execution_links: List[str] = (),
        stopping_conditions: List[Fact] = ()
    ):
        """
        :param operation:
        :param planning_svc:
        :param min_prob_link_success: minimum probability of link success necessary for it to be executed
        :param min_link_data: minimum number runs of link required to use past statistics on it
        :param excluded_trait_prefixes: list of fact trait prefixes to exclude from probability calculation
        :param debug: flag for planner to log link selection logic
        :param delay_execution_links: link ids whose execution should be delayed to backup
        :param stopping_conditions:
        """
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['bayes_state']
        self.next_bucket = 'bayes_state'
        self.matrix_past_links = None
        self.min_link_data = min_link_data
        self.excluded_trait_prefixes = excluded_trait_prefixes
        self.debug = debug
        self.delay_execution_links = delay_execution_links
        self.min_prob_link_success = min_prob_link_success
        self.links_executed = 0
        self.log = self.planning_svc.log
        if self.debug:
            self.log.debug('Operation started')   

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def bayes_state(self):
        """
        Update past operational data matrix if needed, then run
        top priority link for each agent until operation concluded
        """
        if self.links_executed % UPDATE_AFTER_LINKS == 0:
            past_operation_data = await self.planning_svc.get_service('data_svc').locate('operations')
            self.matrix_past_links = await self._build_past_links_matrix(past_operation_data)

        links_to_use = []
        for agent in self.operation.agents:
            possible_agent_links = await self.planning_svc.get_links(operation=self.operation, agent=agent)
            next_link = await self._get_highest_probability_link(possible_agent_links)
            if next_link:
                links_to_use.append(await self.operation.apply(next_link))
        if len(links_to_use):
            await self.operation.wait_for_links_completion(links_to_use)
            self.links_executed += len(links_to_use)
        else:
            if self.debug:
                self.log.debug('Operation concluded')
            self.next_bucket = None
            self.stopping_condition_met = True
    """ PRIVATE """

    async def _build_past_links_matrix(self, past_operation_data: List[Operation]) -> List[List]:
        """
        Build matrix of links (actions) from past operation data with each link (action) as row
        described by selected features
       
        :param past_operation_data: local past operational data object
        """
        matrix_link_data = []

        for operation in past_operation_data:         
            agent_paw_info_mapping = {
                agent.paw: (agent.contact, agent.trusted, agent.privilege, agent.architecture)
                for agent in operation.agents
            }

            for link in operation.chain:
                link_features = {}
                link_features["Planner"] = operation.planner.name
                link_features["Obfuscator"] = operation.obfuscator
                link_features["Adversary_ID"] = operation.adversary.adversary_id
                link_features["Adversary_Name"] = operation.adversary.name
                link_features["Ability_ID"] = link.ability.ability_id
                link_features["Status"] = link.status
                link_features["Command"] = str(b64decode(link.command).decode('utf-8', errors='ignore').replace('\n', ''))
                link_features["Number_Facts"] = len(link.used)
                link_features["Visibility_Score"] = link.visibility.score
                link_features["Executor_Platform"] = link.executor.platform
                link_features["Executor_Name"] = link.executor.name

                agent_paw = link.paw
                if agent_paw in agent_paw_info_mapping.keys():
                    contact_type, trusted_status, privilege, architecture = agent_paw_info_mapping[agent_paw]
                    link_features["Agent_Protocol"] = contact_type
                    link_features["Trusted_Status"] = trusted_status
                    link_features["Agent_Privilege"] = privilege
                    link_features["Host_Architecture"] = architecture
                else:
                    link_features["Agent_Protocol"] = None
                    link_features["Trusted_Status"] = None
                    link_features["Agent_Privilege"] = None
                    link_features["Host_Architecture"] = None

                link_features["Link_Facts"] = self._get_useful_facts(link)

                link_row = [link_features[feature] for feature in FEATURE_NAMES]
                matrix_link_data.append(link_row)
        return matrix_link_data

    async def _get_highest_probability_link(self, links: List[Link]) -> Union[Link, None]:
        """
        Selects the best link from links or None if all links don't match qualifications. 
        Defaults to atomic ordering for certain configured abilities in delay_execution_links
        parameter.

        :param links: list of links that agent could execute
        """
        link_probability_success = dict()
        link_num_observations = dict()
        links_insufficient_data = []

        for index, link in enumerate(links): 
            # NOTE: link_query_features allows customizing which of
            # FEATURE_NAMES to query by current selection of features
            # with broad scope
            link_query_features = {
                "Ability_ID": str(link.ability.ability_id),
                "Link_Facts": self._get_useful_facts(link),
                "Executor_Platform": str(link.executor.platform)
            }
            prob_link_success, num_link_observations = self._get_link_success_probability(link_query_features)
            if prob_link_success == None or str(link.ability.ability_id) in self.delay_execution_links:
                # NOTE: config delayed links are also treated as insufficient data
                links_insufficient_data.append(link)
            else:
                link_probability_success[index] = prob_link_success
                link_num_observations[index] = num_link_observations

        if len(link_probability_success) == 0:
            return self._backup_atomic_ordering(links_insufficient_data)

        highest_probability_link_index = max(link_probability_success, key=link_probability_success.get)
        prob_success_best_link = link_probability_success[highest_probability_link_index]
        if prob_success_best_link >= self.min_prob_link_success:
            if self.debug:
                self.log.debug(
                    f"Best link selected with probability of success {prob_success_best_link:.2f} " + \
                    f"based on {link_num_observations[highest_probability_link_index]} observations"
                )
            chosen_link = links[highest_probability_link_index]
        else:
            if self.debug:
                self.log.debug(
                    f"Skipping {len(link_probability_success)} link(s) with insufficient likelihood of success"
                )
            chosen_link = None

        return chosen_link

    def _get_useful_facts(self, link: Link) -> Dict[str, str]:
        """
        Selects generalizable facts from link object for data querying
        """
        useful_facts = {
            str(used_fact.trait): str(used_fact.value) for used_fact in link.used
            if not str(used_fact.trait).startswith(self.excluded_trait_prefixes)
        }
        return useful_facts

    def _get_link_success_probability(self, query_features: Dict): 
        """
        Calculates Bayes probability for a link (with features and values
        from query_features) executing successfully. Returns success probability,
        and number of link observations in dataset.
        """
        total_links_count = len(self.matrix_past_links)

        query_features_all_matrix = self._query_link_matrix(
            matrix_link_data=self.matrix_past_links,
            query=query_features)
        query_links_count = len(query_features_all_matrix)
        if query_links_count < self.min_link_data:
            return None, query_links_count

        success_matrix = self._query_link_matrix(
            matrix_link_data=self.matrix_past_links,
            query=dict(Status=0))
        query_features_success_matrix = self._query_link_matrix(
            matrix_link_data=success_matrix,
            query=query_features)
        query_features_success_links_count = len(query_features_success_matrix)
        successful_links_count = len(success_matrix)

        # Bayes applied to queried links (actions)
        prob_a = successful_links_count / total_links_count
        prob_b = query_links_count / total_links_count     
        prob_b_given_a = query_features_success_links_count / successful_links_count
        probability_success = ((prob_b_given_a * prob_a) / prob_b)

        return probability_success, query_links_count

    def _query_link_matrix(self, matrix_link_data: List[List], query: Dict) -> List[List]:
        """
        Query link matrix for links containing specific features
        and values and return new matrix composed of column names row
        and the link rows containing right feat and val

        :param matrix_link_data: link matrix that will be queried
        :param query_features: dict of {feature_names: values} that matrix_link_data will be queried by
        """
        def _check_query_condition(link):
            query_conditions = []
            for feature_name, feature_value in query.items():
                feat_index = FEATURE_NAMES.index(feature_name)
                if feature_name == 'Link_Facts':
                    cur_facts_dict = link[feat_index]
                    for req_fact_type, req_fact_val in query['Link_Facts'].items():
                        # check that current link contains required fact type and required fact value
                        query_condition = req_fact_type in cur_facts_dict and str(cur_facts_dict[req_fact_type]) == str(req_fact_val)
                        query_conditions.append(query_condition)
                else:
                    query_condition = str(link[feat_index]) == str(feature_value)
                    query_conditions.append(query_condition)
            return all(query_conditions)

        queried_link_matrix = [feature_row for feature_row in matrix_link_data if _check_query_condition(feature_row)]

        return queried_link_matrix

    def _backup_atomic_ordering(self, links_insufficient_data: List[Link]) -> Union[Link, None]:
        """
        Select a link based on atomic ordering        
        :param links_insufficient_data: links with insufficient data for probability selection
        """ 
        ability_id_to_link = dict()
        for link in links_insufficient_data:
            ability_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(ability_id_to_link.keys())
        filtered_atomic_ordering = [
            ability_id for ability_id in self.operation.adversary.atomic_ordering
            if ability_id in candidate_ids
        ]
        if len(filtered_atomic_ordering):
            if self.debug:
                self.log.debug("Link selected with backup atomic ordering")
            return ability_id_to_link[filtered_atomic_ordering[0]]
        else:
            return None
