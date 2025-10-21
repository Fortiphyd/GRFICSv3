from reportlab.lib.units import inch
from reportlab.platypus import Paragraph

from plugins.debrief.app.utility.base_report_section import BaseReportSection
from plugins.debrief.app.debrief_svc import DebriefService


class DebriefReportSection(BaseReportSection):
    def __init__(self):
        super().__init__()
        self.id = 'tactic-technique-table'
        self.display_name = 'Tactic and Technique Table'
        self.section_title = 'TACTICS AND TECHNIQUES'
        self.description = ''

    async def generate_section_elements(self, styles, **kwargs):
        flowable_list = []
        if 'operations' in kwargs:
            operations = kwargs.get('operations', [])
            ttps = DebriefService.generate_ttps(operations)
            flowable_list.append(self.group_elements([
                Paragraph(self.section_title, styles['Heading2']),
                self._generate_ttps_table(ttps)
            ]))
        return flowable_list

    def _generate_ttps_table(self, ttps):
        ttp_data = [['Tactics', 'Techniques', 'Abilities']]
        for key, tactic in ttps.items():
            technique_arr = []
            for name, tid in tactic['techniques'].items():
                technique_arr.append(tid + ': ' + name)
            ttp_data.append([tactic['name'].capitalize(), technique_arr, tactic['steps']])
        return self.generate_table(ttp_data, [1.25 * inch, 3.25 * inch, 2 * inch])

    @staticmethod
    def _get_operation_ttps(operations):
        ttps = dict()
        for op in operations:
            for link in op.chain:
                if not link.cleanup:
                    tactic_name = link.ability.tactic
                    if tactic_name not in ttps.keys():
                        tactic = dict(name=tactic_name,
                                      techniques={link.ability.technique_name: link.ability.technique_id},
                                      steps={op.name: [link.ability.name]})
                        ttps[tactic_name] = tactic
                    else:
                        if link.ability.technique_name not in ttps[tactic_name]['techniques'].keys():
                            ttps[tactic_name]['techniques'][link.ability.technique_name] = link.ability.technique_id
                        if op.name not in ttps[tactic_name]['steps'].keys():
                            ttps[tactic_name]['steps'][op.name] = [link.ability.name]
                        elif link.ability.name not in ttps[tactic_name]['steps'][op.name]:
                            ttps[tactic_name]['steps'][op.name].append(link.ability.name)
        return dict(sorted(ttps.items()))
