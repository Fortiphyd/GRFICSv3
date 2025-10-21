import logging
from app.utility.base_parser import BaseParser, PARSER_SIGNALS_FAILURE


class Parser(BaseParser):
    checked_flags = list('FullyQualifiedErrorId')

    def parse(self, blob):
        for ex_line in self.line(blob):
            if any(x in ex_line for x in self.checked_flags):
                log = logging.getLogger('parsing_svc')
                log.warning('This ability failed for some reason. Manually updating the link to report a failed state.')
                return [PARSER_SIGNALS_FAILURE]
        return []
