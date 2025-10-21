from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return Shared()


class Shared(Extension):

    def __init__(self):
        super().__init__([
            ('shared.go', 'shared'),
        ])
        self.dependencies = []
