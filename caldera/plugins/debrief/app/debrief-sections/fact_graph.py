from reportlab.lib.units import inch

from plugins.debrief.app.utility.base_report_section import BaseReportSection


class DebriefReportSection(BaseReportSection):
    def __init__(self):
        super().__init__()
        self.id = 'fact-graph'
        self.display_name = 'Fact Graph'
        self.section_title = 'FACT GRAPH'
        self.description = 'This graph displays the facts discovered by the operations run. Facts are attached to ' \
                           'the operation where they were discovered. Facts are also attached to the facts that led ' \
                           'to their discovery. For readability, only the first 15 facts discovered in an operation ' \
                           'are included in the graph.'

    async def generate_section_elements(self, styles, **kwargs):
        flowable_list = []
        path = kwargs.get('graph_files', {}).get('fact')
        if path:
            # Keep the title, description, and graph grouped together to avoid page break in the middle.
            flowable_list.append(self.generate_grouped_graph_section_flowables(styles, path, 4*inch))

        return flowable_list
