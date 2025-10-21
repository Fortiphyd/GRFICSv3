from plugins.debrief.app.utility.base_report_section import BaseReportSection


class DebriefReportSection(BaseReportSection):
    def __init__(self):
        super().__init__()
        self.id = 'agents'
        self.display_name = 'Agents'
        self.section_title = 'AGENTS'
        self.description = 'The table below displays information about the agents used. An agent\'s paw is the unique' \
                           ' identifier, or paw print, of an agent. Also included are the username of the user who ' \
                           'executed the agent, the privilege level of the agent process, and the name of the agent ' \
                           'executable.'

    async def generate_section_elements(self, styles, **kwargs):
        flowable_list = []
        if 'agents' in kwargs:
            flowable_list.append(self.generate_section_title_and_description(styles))
            agent_data = [['Paw', 'Host', 'Platform', 'Username', 'Privilege', 'Executable']]
            for a in kwargs.get('agents', []):
                agent_data.append(
                    ['<a name="agent-{0}"/>{0}'.format(a.paw), a.host, a.platform, a.username, a.privilege,
                     a.exe_name])
            flowable_list.append(self.generate_table(agent_data, '*'))

        return flowable_list
