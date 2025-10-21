from reportlab.lib.units import inch

from plugins.debrief.app.utility.base_report_section import BaseReportSection


class DebriefReportSection(BaseReportSection):
    def __init__(self):
        super().__init__()
        self.id = 'technique-graph'
        self.display_name = 'Technique Graph'
        self.section_title = 'TECHNIQUE GRAPH'
        self.description = 'This graph displays the order of techniques executed by the operation. A technique ' \
                           'explains the technical method or the "how" of a step.'

    async def generate_section_elements(self, styles, **kwargs):
        flowable_list = []
        path = kwargs.get('graph_files', {}).get('technique')
        if path:
            # Keep the title, description, and graph grouped together to avoid page break in the middle.
            flowable_list.append(self.generate_grouped_graph_section_flowables(styles, path, 4*inch))

        return flowable_list
