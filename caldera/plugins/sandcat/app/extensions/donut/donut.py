from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return Donut()


class Donut(Extension):

    def __init__(self):
        directory = 'execute/donut'
        super().__init__([
            ('donut.go', directory),
            ('dll_windows.go', directory),
            ('donut_windows.go', directory),
            ('donut_helper_windows.go', directory)
        ])
        self.dependencies = []
