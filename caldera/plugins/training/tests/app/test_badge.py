import pytest

from plugins.training.app import errors
from plugins.training.app.c_badge import Badge
from plugins.training.app.c_flag import Flag


class FakeFlag(Flag):
    name = "Test Flag"
    challenge = "Run the tests"
    extra_info = "Need to use pytest to run the tests"

    async def verify(self, services):
        return True


class TestBadge:

    def test_find_flag(self):
        badge1 = Badge(name="foo-badge-1")
        flag1 = FakeFlag(number=1)
        badge1.flags.append(flag1)
        found = badge1.get_flag(flag_name=flag1.name)
        assert found is flag1

    def test_find_flag_fail(self):
        badge1 = Badge(name="foo-badge-1")
        flag1 = FakeFlag(number=1)
        badge1.flags.append(flag1)

        with pytest.raises(errors.FlagDoesNotExist):
            badge1.get_flag(flag_name='DOES NOT EXIST')
