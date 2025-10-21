import pytest

from app.objects.secondclass.c_link import Link
from plugins.emu.app.group_filtered_planner import LogicalPlanner


BUCKET_NAME = 'fetch_and_run_links'


class DummyOperation:
    def __init__(self, dummy_adversary, dummy_agents):
        self.adversary = dummy_adversary
        self.agents = dummy_agents

    async def wait_for_links_completion(self, _):
        return

    async def apply(self, link):
        return link


class DummyAdversary:
    def __init__(self, atomic_ordering):
        self.atomic_ordering = atomic_ordering


class DummyAgent:
    def __init__(self, paw, group):
        self.paw = paw
        self.group = group


class DummyAbility:
    def __init__(self, ability_id):
        self.ability_id = ability_id


@pytest.fixture
def dummy_agents():
    return [
        DummyAgent('paw1', 'group1'),
        DummyAgent('paw2', 'group2'),
        DummyAgent('paw3', 'group3'),
        DummyAgent('paw4', 'group1'),
        DummyAgent('paw5', 'group4'),
    ]


@pytest.fixture
def pending_links():
    return [
        Link(command='test command', paw='paw1', ability=DummyAbility('123')),
        Link(command='test command variant', paw='paw1', ability=DummyAbility('123')),
        Link(command='test command', paw='paw2', ability=DummyAbility('123')),
        Link(command='test command', paw='paw3', ability=DummyAbility('123')),
    ]


@pytest.fixture
def potential_links_dict():
    return {
        'paw1': [
            Link(command='test command', paw='paw1', ability=DummyAbility('123')),
            Link(command='test command variant', paw='paw1', ability=DummyAbility('123')),
            Link(command='test command', paw='paw1', ability=DummyAbility('456')),
            Link(command='test command', paw='paw1', ability=DummyAbility('1011')),
        ],
        'paw2': [
            Link(command='test command', paw='paw2', ability=DummyAbility('123')),
        ],
        'paw3': [
            Link(command='test command', paw='paw3', ability=DummyAbility('1011')),
        ],
        'paw4': [
           Link(command='test command', paw='paw4', ability=DummyAbility('456')),
        ],
    }


@pytest.fixture
def potential_links_list():
    return [
        Link(command='test command', paw='paw1', ability=DummyAbility('123')),
        Link(command='test command variant', paw='paw1', ability=DummyAbility('123')),
        Link(command='test command', paw='paw1', ability=DummyAbility('456')),
        Link(command='test command', paw='paw2', ability=DummyAbility('123')),
        Link(command='test command', paw='paw3', ability=DummyAbility('1011')),
        Link(command='test command', paw='paw4', ability=DummyAbility('456')),
        Link(command='test command', paw='paw1', ability=DummyAbility('1011')),
    ]


@pytest.fixture
def sample_abilities():
    return ['123', '456', '789', '1011']


@pytest.fixture
def sample_filter():
    return {
        '123': ['group1'],
        '789': ['group2'],
        '1011': ['group1', 'group3'],
    }


@pytest.fixture
def generate_planner(potential_links_dict):
    async def _get_links_mock(agent):
        return potential_links_dict.get(agent.paw, [])

    def _generate_planner(atomic_ordering, agents, filtered_groups_by_ability=None):
        operation = DummyOperation(DummyAdversary(atomic_ordering), agents)
        planner = LogicalPlanner(operation, None, filtered_groups_by_ability=filtered_groups_by_ability)
        planner._get_links = _get_links_mock
        return planner
    return _generate_planner


@pytest.fixture
def planner_without_filter(generate_planner, dummy_agents, sample_abilities):
    return generate_planner(sample_abilities, dummy_agents)


@pytest.fixture
def filtered_planner(generate_planner, dummy_agents, sample_abilities, sample_filter):
    return generate_planner(sample_abilities, dummy_agents, filtered_groups_by_ability=sample_filter)


class TestGroupFilteredPlanner:
    async def test_fetch_from_pending_links(self, planner_without_filter, pending_links):
        planner_without_filter.pending_links = pending_links
        links_to_use = planner_without_filter._fetch_from_pending_links()
        assert len(links_to_use) == 3
        assert len(planner_without_filter.pending_links) == 1
        assert links_to_use[0].paw == 'paw1' and links_to_use[0].ability.ability_id == '123'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[1].paw == 'paw2'
        assert links_to_use[2].paw == 'paw3'
        assert planner_without_filter.pending_links[0].paw == 'paw1'
        assert planner_without_filter.pending_links[0].command == 'test command variant'

    async def test_fetch_from_empty_pending_links(self, planner_without_filter):
        links_to_use = planner_without_filter._fetch_from_pending_links()
        assert not links_to_use
        assert not planner_without_filter.pending_links

    async def test_get_valid_agents_for_abil_without_filter(self, planner_without_filter):
        assert len(planner_without_filter.operation.agents) == 5
        valid_agents = planner_without_filter._get_valid_agents_for_ability('123')
        assert len(valid_agents) == 5

    async def test_get_pending_links_without_filter(self, planner_without_filter):
        links = await planner_without_filter._get_pending_links('123')
        assert len(links) == 3
        assert links[0].paw == 'paw1'
        assert links[0].ability.ability_id == '123'
        assert links[0].command == 'test command'
        assert links[1].paw == 'paw1'
        assert links[1].ability.ability_id == '123'
        assert links[1].command == 'test command variant'
        assert links[2].paw == 'paw2'
        assert links[2].ability.ability_id == '123'
        assert links[2].command == 'test command'

    async def test_fetch_links_without_filter(self, planner_without_filter):
        assert not planner_without_filter.pending_links
        assert planner_without_filter.current_ability_index == 0

        # first pass
        links_to_use = await planner_without_filter._fetch_links()
        assert len(planner_without_filter.pending_links) == 1
        assert planner_without_filter.pending_links[0].paw == 'paw1'
        assert planner_without_filter.pending_links[0].command == 'test command variant'
        assert planner_without_filter.pending_links[0].ability.ability_id == '123'
        assert planner_without_filter.current_ability_index == 1
        assert len(links_to_use) == 2
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[0].ability.ability_id == '123'
        assert links_to_use[1].paw == 'paw2'
        assert links_to_use[1].command == 'test command'
        assert links_to_use[1].ability.ability_id == '123'

        # second pass - finishes links from first pass
        links_to_use = await planner_without_filter._fetch_links()
        assert len(planner_without_filter.pending_links) == 0
        assert planner_without_filter.current_ability_index == 1
        assert len(links_to_use) == 1
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command variant'
        assert links_to_use[0].ability.ability_id == '123'

        # third pass - ability #2
        links_to_use = await planner_without_filter._fetch_links()
        assert len(planner_without_filter.pending_links) == 0
        assert planner_without_filter.current_ability_index == 2
        assert len(links_to_use) == 2
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[0].ability.ability_id == '456'
        assert links_to_use[1].paw == 'paw4'
        assert links_to_use[1].command == 'test command'
        assert links_to_use[1].ability.ability_id == '456'

        # fourth pass - skip ability #3 and go to #4
        links_to_use = await planner_without_filter._fetch_links()
        assert len(planner_without_filter.pending_links) == 0
        assert planner_without_filter.current_ability_index == 4
        assert len(links_to_use) == 2
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[0].ability.ability_id == '1011'
        assert links_to_use[1].paw == 'paw3'
        assert links_to_use[1].command == 'test command'
        assert links_to_use[1].ability.ability_id == '1011'

        # fifth pass - end
        links_to_use = await planner_without_filter._fetch_links()
        assert len(planner_without_filter.pending_links) == 0
        assert planner_without_filter.current_ability_index == 4
        assert len(links_to_use) == 0

    async def test_get_valid_agents_for_abil_with_filter(self, filtered_planner):
        assert len(filtered_planner.operation.agents) == 5
        valid_agent_paws = [agent.paw for agent in filtered_planner._get_valid_agents_for_ability('123')]
        assert len(valid_agent_paws) == 2
        assert 'paw1' in valid_agent_paws
        assert 'paw4' in valid_agent_paws
        valid_agent_paws = [agent.paw for agent in filtered_planner._get_valid_agents_for_ability('456')]
        assert len(valid_agent_paws) == 5
        valid_agent_paws = [agent.paw for agent in filtered_planner._get_valid_agents_for_ability('789')]
        assert len(valid_agent_paws) == 1
        assert 'paw2' in valid_agent_paws

    async def test_get_pending_links_with_filter(self, filtered_planner):
        links = await filtered_planner._get_pending_links('123')
        assert len(links) == 2
        assert links[0].paw == 'paw1'
        assert links[0].ability.ability_id == '123'
        assert links[0].command == 'test command'
        assert links[1].paw == 'paw1'
        assert links[1].ability.ability_id == '123'
        assert links[1].command == 'test command variant'

        links = await filtered_planner._get_pending_links('456')
        assert len(links) == 2
        assert links[0].paw == 'paw1'
        assert links[0].ability.ability_id == '456'
        assert links[0].command == 'test command'
        assert links[1].paw == 'paw4'
        assert links[1].ability.ability_id == '456'
        assert links[1].command == 'test command'

        links = await filtered_planner._get_pending_links('1011')
        assert len(links) == 2
        assert links[0].paw == 'paw1'
        assert links[0].ability.ability_id == '1011'
        assert links[0].command == 'test command'
        assert links[1].paw == 'paw3'
        assert links[1].ability.ability_id == '1011'
        assert links[1].command == 'test command'

    async def test_fetch_links_with_filter(self, filtered_planner):
        assert not filtered_planner.pending_links
        assert filtered_planner.current_ability_index == 0

        # first pass
        links_to_use = await filtered_planner._fetch_links()
        assert len(filtered_planner.pending_links) == 1
        assert filtered_planner.pending_links[0].paw == 'paw1'
        assert filtered_planner.pending_links[0].command == 'test command variant'
        assert filtered_planner.pending_links[0].ability.ability_id == '123'
        assert filtered_planner.current_ability_index == 1
        assert len(links_to_use) == 1
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[0].ability.ability_id == '123'

        # second pass - finishes links from first pass
        links_to_use = await filtered_planner._fetch_links()
        assert len(filtered_planner.pending_links) == 0
        assert filtered_planner.current_ability_index == 1
        assert len(links_to_use) == 1
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command variant'
        assert links_to_use[0].ability.ability_id == '123'

        # third pass - ability #2
        links_to_use = await filtered_planner._fetch_links()
        assert len(filtered_planner.pending_links) == 0
        assert filtered_planner.current_ability_index == 2
        assert len(links_to_use) == 2
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[0].ability.ability_id == '456'
        assert links_to_use[1].paw == 'paw4'
        assert links_to_use[1].command == 'test command'
        assert links_to_use[1].ability.ability_id == '456'

        # fourth pass - skip ability #3 and go to #4
        links_to_use = await filtered_planner._fetch_links()
        assert len(filtered_planner.pending_links) == 0
        assert filtered_planner.current_ability_index == 4
        assert len(links_to_use) == 2
        assert links_to_use[0].paw == 'paw1'
        assert links_to_use[0].command == 'test command'
        assert links_to_use[0].ability.ability_id == '1011'
        assert links_to_use[1].paw == 'paw3'
        assert links_to_use[1].command == 'test command'
        assert links_to_use[1].ability.ability_id == '1011'

        # fifth pass - end
        links_to_use = await filtered_planner._fetch_links()
        assert len(filtered_planner.pending_links) == 0
        assert filtered_planner.current_ability_index == 4
        assert len(links_to_use) == 0
