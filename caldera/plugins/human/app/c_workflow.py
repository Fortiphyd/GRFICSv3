from app.utility.base_object import BaseObject


class Workflow(BaseObject):

    @property
    def display(self):
        return self.clean(dict(name=self.name, description=self.description, file=self.file))

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    def __init__(self, name, description, file):
        super().__init__()
        self.name = name
        self.description = description
        self.file = file

    def store(self, ram):
        existing = self.retrieve(ram['workflows'], self.unique)
        if not existing:
            ram['workflows'].append(self)
            return self.retrieve(ram['workflows'], self.unique)
        return existing
