from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return Shellcode()


class Shellcode(Extension):

    def __init__(self):
        super().__init__([
            ('*', 'execute/shellcode'),
        ])
        self.dependencies = []
