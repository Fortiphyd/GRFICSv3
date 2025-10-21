import base64
import glob
import logging
import os
import re

from aiohttp import web
from aiohttp_jinja2 import template
from datetime import datetime
from importlib import import_module
from io import BytesIO
from reportlab import rl_settings
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Spacer

from app.service.auth_svc import for_all_public_methods, check_authorization
from app.utility.base_world import BaseWorld
from plugins.debrief.app.debrief_svc import DebriefService
from plugins.debrief.app.objects.c_story import Story


@for_all_public_methods(check_authorization)
class DebriefGui(BaseWorld):
    def __init__(self, services):
        self.services = services
        self.debrief_svc = DebriefService(services)
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')
        self.file_svc = services.get('file_svc')
        self.log = logging.getLogger('debrief_gui')
        self.uploads_dir = os.path.relpath(os.path.join('plugins', 'debrief', 'uploads'))

        self._suppress_logs('PIL')
        self._suppress_logs('svglib')
        self.report_section_modules = dict()
        self.report_section_names = list()
        self.loaded_report_sections = False

        rl_settings.trustedHosts = BaseWorld.get_config(prop='reportlab_trusted_hosts', name='debrief') or None

    async def _get_access(self, request):
        return dict(access=tuple(await self.auth_svc.get_permissions(request)))

    @template('debrief.html')
    async def splash(self, request):
        operations = [o.display for o in
                      await self.data_svc.locate('operations', match=await self._get_access(request))]
        uploaded_logos_dir = os.path.relpath(os.path.join(self.uploads_dir, 'header-logos'))
        header_logos = [filename for filename in os.listdir(uploaded_logos_dir) if os.path.isfile(
            os.path.relpath(os.path.join(uploaded_logos_dir, filename))
        ) and not filename.startswith('.')]
        try:
            plugins = await self.data_svc.locate('plugins', match=dict(enabled=True))
            self._load_report_sections(plugins)
        except Exception as e:
            print(e)
        return dict(operations=operations, header_logos=header_logos, report_sections=self.report_section_names)

    async def report_sections(self, request):
        try:
            plugins = await self.data_svc.locate('plugins', match=dict(enabled=True))
            self._load_report_sections(plugins)
        except Exception as e:
            print(e)
        report_sections = self.report_section_names
        return web.json_response(dict(report_sections=report_sections))

    async def report(self, request):
        data = dict(await request.json())
        operations = [o for o in await self.data_svc.locate('operations', match=await self._get_access(request))
                      if str(o.id) in data.get('operations')]
        op_displays = [o.display for o in operations]
        ttps = DebriefService.generate_ttps(operations)
        return web.json_response(dict(operations=op_displays, ttps=ttps))

    async def graph(self, request):
        graphs = {
            'steps': self.debrief_svc.build_steps_d3,
            'attackpath': self.debrief_svc.build_attackpath_d3,
            'fact': self.debrief_svc.build_fact_d3,
            'tactic': self.debrief_svc.build_tactic_d3,
            'technique': self.debrief_svc.build_technique_d3
        }
        try:
            graph_type = request.rel_url.query['type']
            operations = request.rel_url.query['operations'].split(',')
            graph = await graphs[graph_type](operations)
            return web.json_response(graph)
        except Exception as e:
            self.log.error(repr(e), exc_info=True)

    async def download_pdf(self, request):
        data = dict(await request.json())
        svg_data = data['graphs']
        header_logo_filename = data.get('header-logo')
        self._save_svgs(svg_data)
        if data['operations']:
            header_logo_path = None
            if header_logo_filename:
                header_logo_path = os.path.relpath(os.path.join(self.uploads_dir, 'header-logos', header_logo_filename))
            operations = [o for o in await self.data_svc.locate('operations', match=await self._get_access(request))
                          if str(o.id) in data.get('operations')]
            filename = 'debrief_' + datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
            agents = await self.data_svc.locate('agents')
            pdf_bytes = await self._build_pdf(operations, agents, filename, data['report-sections'], header_logo_path)
            self._clean_downloads()
            return web.json_response(dict(filename=filename, pdf_bytes=pdf_bytes))
        return web.json_response('No operations selected')

    async def download_json(self, request):
        data = dict(await request.json())
        if data['operations']:
            operations = [await o.report(file_svc=self.file_svc, data_svc=self.data_svc, output=True) for o in
                          await self.data_svc.locate('operations', match=await self._get_access(request))
                          if str(o.id) in data.get('operations')]
            filename = 'debrief_' + datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
            return web.json_response(dict(filename=filename, json_bytes=operations))
        return web.json_response('No operations selected')

    async def all_logos(self, request):
        uploaded_logos_dir = os.path.relpath(os.path.join(self.uploads_dir, 'header-logos'))
        logos = [filename for filename in os.listdir(uploaded_logos_dir) if os.path.isfile(
            os.path.relpath(os.path.join(uploaded_logos_dir, filename))
        ) and not filename.startswith('.')]
        return web.json_response(dict(logos=logos))

    async def upload_logo(self, request):
        data = await request.post()
        logo_file_info = data['header-logo']
        if logo_file_info:
            logo_file = logo_file_info.file
            content = logo_file.read()
            sanitized_filename = self._sanitize_filename(logo_file_info.filename)
            try:
                self._save_uploaded_image(sanitized_filename, content)
            except Exception as e:
                return web.json_response(str(e))
            return web.json_response({"filename": sanitized_filename})
        return web.json_response('No header logo file provided.')

    def _save_uploaded_image(self, filename, content):
        filepath = os.path.relpath(os.path.join(self.uploads_dir, 'header-logos', filename))
        with open(filepath, 'wb') as f:
            f.write(content)

    def _load_report_sections(self, plugins):
        if not self.loaded_report_sections:
            for plugin in plugins:
                if plugin.name:
                    report_sections_dir = os.path.relpath(
                        os.path.join('plugins', plugin.name, 'app', 'debrief-sections'))
                    if os.path.isdir(report_sections_dir):
                        for filepath in glob.iglob('%s/*.py' % report_sections_dir):
                            module_name = filepath.replace('/', '.').replace('\\', '.').replace('.py', '')
                            module = import_module(module_name)
                            if module:
                                module_obj = module.DebriefReportSection()
                                safe_id = re.sub('[^A-Za-z0-9-_:.]', '', re.sub('\s+', '-', module_obj.id))
                                self.report_section_modules[safe_id] = module_obj
                                self.report_section_names.append({ 'key': safe_id, 'name': module_obj.display_name})
                            else:
                                self.log.error("Failed to load debrief report section module %s" % module_name)
            self.loaded_report_sections = True

    async def _build_pdf(self, operations, agents, filename, sections, header_logo_path):
        # pdf setup
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=84, bottomMargin=84, title=filename)
        story_obj = Story()
        story_obj.set_header_logo_path(header_logo_path)
        styles = getSampleStyleSheet()

        story_obj.append(Spacer(1, 36))

        # Add selected module components
        graph_files = dict()
        if any(v for v in sections if '-graph' in v):
            for file in glob.glob('./plugins/debrief/downloads/*.svg'):
                graph_files[os.path.basename(file).split('.')[0]] = file

        # content generation
        try:
            for section in sections:
                section_module = self.report_section_modules.get(section, None)
                if section_module:
                    flowables = await section_module.generate_section_elements(
                        styles,
                        operations=operations,
                        agents=agents,
                        graph_files=graph_files,
                    )
                    for flowable in flowables:
                        story_obj.append(flowable)
                else:
                    self.log.error("Requested debrief section module %s not found." % section)

            # pdf teardown
            doc.build(story_obj.story_arr,
                      onFirstPage=story_obj.header_footer_first,
                      onLaterPages=story_obj.header_footer_rest)
        except Exception as e:
            self.log.error(e)
        pdf_value = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_value.decode('utf-8', errors='ignore')

    @staticmethod
    def _sanitize_filename(filename):
        _, split_name = os.path.split(filename)
        cleaned = re.sub(r'(?u)[^-\w._]', '', split_name).strip()
        return re.sub(r'\s+', '_', cleaned)

    @staticmethod
    def _save_svgs(svgs):
        for filename, svg_bytes in svgs.items():
            save_location = './plugins/debrief/downloads/'
            with open(save_location + filename + '.svg', "wb") as fh:
                fh.write(base64.b64decode(svg_bytes))

    @staticmethod
    def _clean_downloads():
        imgs = []
        imgs.extend(glob.glob('./plugins/debrief/downloads/*.png'))
        imgs.extend(glob.glob('./plugins/debrief/downloads/*.svg'))
        for f in imgs:
            os.remove(f)

    @staticmethod
    def _suppress_logs(library):
        lib = logging.getLogger(library)
        lib.setLevel(logging.INFO)
