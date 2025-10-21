from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return NativeAwsExecutor()


class NativeAwsExecutor(Extension):

    def __init__(self):
        super().__init__([
            ('native.go', 'execute/native'),
            ('*', 'execute/native/aws'),
            ('util.go', 'execute/native/util'),
        ])
        self.dependencies = [
            'github.com/aws/aws-sdk-go',
            'github.com/aws/aws-sdk-go/aws',
        ]
