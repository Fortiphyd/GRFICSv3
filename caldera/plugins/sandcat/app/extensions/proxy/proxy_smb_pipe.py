from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return ProxySmbPipe()


class ProxySmbPipe(Extension):

    def __init__(self):
        super().__init__([
            ('proxy_smb_pipe.go', 'proxy'),
            ('proxy_smb_pipe_util.go', 'proxy'),
        ])
        self.dependencies = ['gopkg.in/natefinch/npipe.v2']
