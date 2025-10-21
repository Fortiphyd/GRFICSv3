from plugins.debrief.app.utility.base_report_section import BaseReportSection


class DebriefReportSection(BaseReportSection):
    def __init__(self):
        super().__init__()
        self.id = 'statistics'
        self.display_name = 'Statistics'
        self.section_title = 'STATISTICS'
        self.description = 'An operation\'s planner makes up the decision making process. It contains logic for how ' \
                           'a running operation should make decisions about which abilities to use and in what order.' \
                           ' An objective is a collection of fact targets, called goals, which can be tied to ' \
                           'adversaries. During the course of an operation, every time the planner is evaluated, the ' \
                           'current objective status is evaluated in light of the current knowledge of the ' \
                           'operation, with the operation completing should all goals be met.'

    async def generate_section_elements(self, styles, **kwargs):
        flowable_list = []
        if 'operations' in kwargs:
            operations = kwargs.get('operations', [])
            flowable_list.append(self.generate_section_title_and_description(styles))
            data = [['Name', 'State', 'Planner', 'Objective', 'Time']]
            for o in operations:
                finish = o.finish if o.finish else 'Not finished'
                data.append([o.name, o.state, o.planner.name, o.objective.name, finish])
            flowable_list.append(self.generate_table(data, '*'))

        return flowable_list
