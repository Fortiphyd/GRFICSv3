from reportlab.lib.units import inch

from plugins.debrief.app.utility.base_report_section import BaseReportSection


class DebriefReportSection(BaseReportSection):
    def __init__(self):
        super().__init__()
        self.id = 'attackpath-graph'
        self.display_name = 'Attack Path Graph'
        self.section_title = 'ATTACK PATH GRAPH'
        self.description = 'This graph displays the attack path of hosts compromised by Caldera. Source and target ' \
                           'hosts are connected by the method of execution used to start the agent on the target host.'

    async def generate_section_elements(self, styles, **kwargs):
        flowable_list = []
        path = kwargs.get('graph_files', {}).get('attackpath')
        if path:
            # Keep the title, description, and graph grouped together to avoid page break in the middle.
            flowable_list.append(self.generate_grouped_graph_section_flowables(styles, path, 4*inch))

        return flowable_list
