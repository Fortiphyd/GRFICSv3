import pytest

from app.utility.base_world import BaseWorld
from plugins.training.app import errors
from plugins.training.app.c_badge import Badge
from plugins.training.app.c_flag import Flag
from plugins.training.app.c_certification import Certification


class FakeFlag(Flag):
    name = "Test Flag"
    challenge = "Run the tests"
    extra_info = "Need to use pytest to run the tests"

    async def verify(self, services):
        return True


class TestCertification:

    def test_find_badge(self):
        certification = Certification(
            identifier="foo",
            name="test-certification",
            description="used for tests",
            access=BaseWorld.Access.RED
        )

        badge1 = Badge(name="foo-badge-1")
        badge2 = Badge(name="foo-badge-2")

        certification.badges.extend([badge1, badge2])

        found = certification.get_badge("foo-badge-1")
        assert found is badge1

    def test_find_badge_fail(self):
        certification = Certification(
            identifier="foo",
            name="test-certification",
            description="used for tests",
            access=BaseWorld.Access.RED
        )

        certification.badges.append(Badge(name="foo-badge-1"))

        with pytest.raises(errors.BadgeDoesNotExist):
            certification.get_badge("DOES NOT EXIST")

    def test_find_flag(self):
        certification = Certification(
            identifier="foo",
            name="test-certification",
            description="used for tests",
            access=BaseWorld.Access.RED
        )

        badge1 = Badge(name="foo-badge-1")
        flag1 = FakeFlag(number=1)

        badge1.flags.append(flag1)
        certification.badges.append(badge1)

        found = certification.get_flag(badge_name=badge1.name, flag_name=flag1.name)
        assert found is flag1

    def test_find_flag_fail(self):
        certification = Certification(
            identifier="foo",
            name="test-certification",
            description="used for tests",
            access=BaseWorld.Access.RED
        )

        badge1 = Badge(name="foo-badge-1")
        flag1 = FakeFlag(number=1)

        badge1.flags.append(flag1)
        certification.badges.append(badge1)

        with pytest.raises(errors.BadgeDoesNotExist):
            certification.get_flag(badge_name='DOES NOT EXIST', flag_name=flag1.name)

        with pytest.raises(errors.FlagDoesNotExist):
            certification.get_flag(badge_name=badge1.name, flag_name='DOES NOT EXIST')
