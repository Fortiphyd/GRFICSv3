from app.utility.base_service import BaseService


class TermService(BaseService):

    def __init__(self, services):
        self.log = self.add_service('term_svc', self)
        tcp_conn = [c for c in services.get('contact_svc').contacts if c.name == 'tcp']
        self.socket_conn = tcp_conn[0]
