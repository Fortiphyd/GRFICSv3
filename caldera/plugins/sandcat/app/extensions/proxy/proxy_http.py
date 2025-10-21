from plugins.sandcat.app.utility.base_extension import Extension


def load():
    return ProxyHttp()


class ProxyHttp(Extension):

    def __init__(self):
        super().__init__([('proxy_receiver_http.go', 'proxy')])
        self.dependencies = []
