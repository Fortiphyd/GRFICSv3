from app.utility.base_object import BaseObject

from plugins.training.app import errors


class Badge(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    @property
    def display(self):
        return dict(name=self.name, flags=[f.display for f in self.flags])

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.flags = []

    def get_flag(self, flag_name):
        """Return a Flag with a matching `name`.

        Raises:
            FlagDoesNotExist: If no Flag is found with a matching `name`
        """
        for flag in self.flags:
            if flag.name == flag_name:
                return flag

        raise errors.FlagDoesNotExist
