from app.utility.base_object import BaseObject

from plugins.training.app import errors


class Certification(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.identifier)

    @property
    def display(self):
        return dict(name=self.name, description=self.description, badges=[b.display for b in self.badges])

    def __init__(self, identifier, name, description, access):
        super().__init__()
        self.identifier = identifier
        self.name = name
        self.description = description
        self.access = access
        self.badges = []

    def store(self, ram):
        existing = self.retrieve(ram['certifications'], self.unique)
        if not existing:
            ram['certifications'].append(self)
            return self.retrieve(ram['certifications'], self.unique)
        return existing

    def get_badge(self, badge_name):
        """Return a Badge instance for the input badge name.

        Raises:
            BadgeDoesNotExist: if no badge is found with a matching name.
        """
        for badge in self.badges:
            if badge.name == badge_name:
                return badge

        raise errors.BadgeDoesNotExist

    def get_flag(self, badge_name, flag_name):
        """Return a Flag instance for the input badge name and flag name.

        Raises:
            BadgeDoesNotExist: if no badge is found with a matching name.
            FlagDoesNotExist: if no flag exists with a matching name under the input badge.
        """
        badge = self.get_badge(badge_name)
        return badge.get_flag(flag_name)
