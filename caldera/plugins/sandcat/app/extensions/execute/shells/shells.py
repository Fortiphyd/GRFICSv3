from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return Shells()


class Shells(Extension):

    def __init__(self):
        super().__init__([
            ('osascript.go', 'execute/shells'),
            ('powershell_core.go', 'execute/shells'),
            ('python.go', 'execute/shells')
        ])
        self.dependencies = []
