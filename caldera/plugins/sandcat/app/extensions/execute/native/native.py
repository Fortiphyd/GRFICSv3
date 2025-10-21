from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return NativeExecutor()


class NativeExecutor(Extension):

    def __init__(self):
        super().__init__([
            ('native.go', 'execute/native'),
            ('*', 'execute/native/discovery'),
            ('util.go', 'execute/native/util'),
        ])
        self.dependencies = []
